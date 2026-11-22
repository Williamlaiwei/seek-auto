// Local browser integration check; fake jobs and AI use an isolated, disposable DB.
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile, unlink } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';

const root=dirname(fileURLToPath(import.meta.url));
const local=resolve(root,'.local');await mkdir(local,{recursive:true});
const id=randomUUID(), database=resolve(local,`browser-${id}.sqlite3`);
const profile=resolve(local,`chrome-${id}`);
const program=`import sys; import server
server.DATA=server.Path(sys.argv[1])
server.seek.fetch_page=lambda *args: {'data':[{'id':12345678,'title':'Python Engineer','companyName':'Example Studio','locations':[{'label':'Sydney NSW'}],'teaser':'Build Python services in a hybrid team.','salaryLabel':'AUD 100,000 - 120,000'}]}
server.seek.fetch_detail=lambda job_id: {'id':str(job_id),'title':'Python Engineer','company':'Example Studio','description':'Build Python APIs with a Sydney team. Three years of Python experience required. Hybrid role.','url':'https://www.seek.com.au/job/'+str(job_id)}
letter='''Dear Hiring Manager,

I am writing to apply for the Python Engineer position at Example Studio. My experience building Python APIs and working with databases aligns with the practical engineering focus of this role.

Over five years, I have developed backend services and designed database structures to support reliable applications. I would bring that experience to your team, along with a direct and collaborative approach to solving technical problems.

I am interested in the opportunity to contribute to a Sydney-based team working on useful, well-maintained services. I would welcome the chance to discuss how my background could support your current projects.

Thank you for considering my application.

Kind regards,'''
server.completion=lambda *args: {'ok':True,'score':82,'verdict':'Apply','summary':'Python experience matches; work rights still need confirmation.','strengths':['Experience building Python APIs'],'gaps':['Confirm the cloud technologies used by the team'],'must_confirm':['Australian work rights'],'next_steps':['Prepare relevant project evidence'],'cover_letter':letter}
server.ThreadingHTTPServer(('127.0.0.1',18765),server.Handler).serve_forever()
`;
const backend=spawn('python',['-c',program,database],{cwd:root,windowsHide:true,stdio:['ignore','ignore','pipe']});
let backendError='';backend.stderr.on('data',d=>backendError+=d);
const chrome=spawn(process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',[
  '--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'
],{windowsHide:true,stdio:['ignore','ignore','pipe']});
let chromeError='';chrome.stderr.on('data',d=>chromeError+=d);
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let socket;
try{
  let port;
  for(let n=0;n<100;n++){
    try{port=Number((await readFile(resolve(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);break;}catch{}
    if(chrome.exitCode!==null)throw Error(`Chrome exited: ${chromeError.slice(-600)}`);
    await pause(100);
  }
  assert.ok(port,'Chrome debugging did not start');
  for(let n=0;n<100;n++){
    try{const r=await fetch('http://127.0.0.1:18765/api/state');if(r.ok)break;}catch{}
    if(backend.exitCode!==null)throw Error(`Backend exited: ${backendError}`);
    await pause(100);
  }
  const targets=await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
  let sequence=0;const pending=new Map(),errors=[];
  socket.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const entry=pending.get(m.id);pending.delete(m.id);if(m.error)entry.reject(Error(m.error.message));else entry.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);};
  const command=(method,params={})=>new Promise((resolve,reject)=>{const requestId=++sequence;pending.set(requestId,{resolve,reject});socket.send(JSON.stringify({id:requestId,method,params}));});
  const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
  const until=async expression=>{for(let n=0;n<100;n++){if(await evaluate(expression))return;await pause(80);}throw Error(`Timed out: ${expression}`);};
  await command('Runtime.enable');await command('Page.enable');
  await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
  await command('Page.navigate',{url:'http://127.0.0.1:18765'});
  await until(`document.querySelector('#total-count')?.textContent==='0' && typeof ready==='function'`);
  await evaluate(`document.querySelector('#job-url').value='https://www.seek.com.au/job/12345678';document.querySelector('#import-form').requestSubmit()`);
  await until(`document.querySelectorAll('.studio-job').length===1 && !state.busy`);
  await evaluate(`document.querySelector('#generate-button').click()`);
  await until(`document.querySelector('#settings-dialog').open`);
  await evaluate(`document.querySelector('#profile').value='Five years of Python experience building APIs and working with databases.';document.querySelector('#model').value='test-model';document.querySelector('#api-key').value='TEST-KEY-NOT-REAL';document.querySelector('#settings-form').requestSubmit()`);
  await until(`!document.querySelector('#settings-dialog').open`);
  await until(`document.querySelector('#letter-editor')?.value.includes('Dear Hiring Manager') && !state.busy`);
  const savedLetter=await evaluate(`document.querySelector('#letter-editor').value`);
  await evaluate(`document.querySelector('#letter-editor').value+=' Extra personal sentence.';document.querySelector('#letter-editor').dispatchEvent(new Event('input',{bubbles:true}))`);
  await until(`document.querySelector('#save-state')?.textContent==='Saved locally'`);
  await command('Browser.grantPermissions',{origin:'http://127.0.0.1:18765',permissions:['clipboardReadWrite','clipboardSanitizedWrite']});
  await command('Page.bringToFront');
  await evaluate(`document.querySelector('#copy-button').click()`);
  await until(`document.querySelector('#copy-button').textContent.includes('copied')`);
  const clipboard=await evaluate(`navigator.clipboard.readText()`);
  assert.equal(clipboard.replace(/\r\n/g,'\n'),savedLetter+' Extra personal sentence.','Clipboard did not contain edited CL');
  assert.equal(await evaluate(`document.querySelector('.apply-link').href`),'https://www.seek.com.au/job/12345678');
  await evaluate(`document.querySelector('#job-status').value='Applied';document.querySelector('#job-status').dispatchEvent(new Event('change',{bubbles:true}))`);
  await until(`document.querySelector('.applied-tag') && !state.busy`);
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true,'Desktop overflow');
  const desktop=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  await writeFile(resolve(local,'preview-desktop.png'),Buffer.from(desktop.data,'base64'));
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await pause(200);
  assert.equal(await evaluate(`document.documentElement.scrollWidth<=innerWidth`),true,'Mobile overflow');
  const mobile=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  await writeFile(resolve(local,'preview-mobile.png'),Buffer.from(mobile.data,'base64'));
  await evaluate(`window.__qa_before_reload=true`);
  await command('Page.reload');
  await until(`!window.__qa_before_reload && document.querySelector('#letter-editor')?.value.includes('Extra personal sentence.')`);
  assert.equal(await evaluate(`document.querySelector('#api-key').value`),'','API key persisted');
  assert.equal(await evaluate(`document.querySelector('#job-status').value`),'Applied');
  assert.ok(!(await readFile(database)).includes(Buffer.from('TEST-KEY-NOT-REAL')),'Key written to DB');
  assert.deepEqual(errors,[],'Browser JS errors');
  await evaluate(`document.querySelector('#settings-button').click();document.querySelector('#api-key').value='TEST-KEY-NOT-REAL';document.querySelector('#settings-dialog').close();document.querySelector('.revision-panel').open=true;document.querySelector('#revision').value='Make it more concise.';document.querySelector('#revise-button').click()`);
  await until(`!state.busy && document.querySelector('#letter-editor')?.value.includes('Dear Hiring Manager')`);
  assert.equal(await evaluate(`selected().letter_history.length`),1,'Previous letter was not archived');
  assert.deepEqual(errors,[],'Browser JS errors');
  console.log('PASS: import, personal settings, CL generation, editing + autosave, real clipboard, apply link, revision, persistence, key privacy, desktop + mobile layout.');
  console.log('Screenshots: .local/preview-desktop.png and .local/preview-mobile.png');
}finally{
  socket?.close();chrome.kill();backend.kill();await pause(500);
  await unlink(database).catch(()=>{});
}
