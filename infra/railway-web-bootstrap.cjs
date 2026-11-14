const { gunzipSync } = require('node:zlib');
const { createHash } = require('node:crypto');
const { mkdirSync, writeFileSync, chownSync, readdirSync, lstatSync } = require('node:fs');
const { resolve, dirname } = require('node:path');
const { spawnSync, spawn } = require('node:child_process');
const env = process.env;
const bytes = Buffer.from(Array.from({length:Number(env.APP_SOURCE_PARTS)},(_,i)=>env[`APP_SOURCE_${i}`]).join(''),'base64');
if(createHash('sha256').update(bytes).digest('hex')!==env.APP_SOURCE_SHA256) throw new Error('Source checksum mismatch');
const root='/repo'; mkdirSync(root,{recursive:true});
for(const [name,content] of Object.entries(JSON.parse(gunzipSync(bytes)))) {
  const target=resolve(root,name); if(!target.startsWith(root+'/')) throw new Error('Invalid source path');
  mkdirSync(dirname(target),{recursive:true}); writeFileSync(target,content);
}
function run(command,args){const r=spawnSync(command,args,{cwd:root,stdio:'inherit',env});if(r.error||r.status!==0)throw new Error(`Build failed: ${command}`);}
run('npm',['install','-g','pnpm@12.11.2']);
run('pnpm',['install','--frozen-lockfile','--filter','@acme-bot/web...']);
run('pnpm',['--filter','@acme-bot/web','build']);
// Permite ao processo sem privilégios ler o build e o cache gerado.
function own(dir){for(const entry of readdirSync(dir)){const p=resolve(dir,entry);if(lstatSync(p).isDirectory())own(p);chownSync(p,1001,1001);}chownSync(dir,1001,1001);}
own('/repo/apps/web/.next');
process.setgid(1001);process.setuid(1001);
const server=spawn(process.execPath,['node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port',env.PORT||'3100'],{cwd:root+'/apps/web',stdio:'inherit',env});
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>server.kill(signal));
server.on('exit',code=>process.exit(code??1));
