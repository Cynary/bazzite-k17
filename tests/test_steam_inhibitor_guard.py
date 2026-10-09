"""Exercise the refused-suspend race without putting a real machine to sleep."""
import ast
import json
from pathlib import Path
import subprocess
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'files/usr/libexec/steam-inhibitor-guard.py'
TREE = ast.parse(SOURCE.read_text())


class GuardTests(unittest.TestCase):
    def test_only_explicit_steam_refusal(self):
        nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'is_denied_sleep']
        env = {'DENIED_SLEEP': 'Error org.freedesktop.login1.BlockedByInhibitorLock:'}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), env)
        predicate = env['is_denied_sleep']
        record = {'SYSLOG_IDENTIFIER': 'steam', '_COMM': 'srt-logger',
                  'MESSAGE': env['DENIED_SLEEP'] + ' Operation denied due to active block inhibitor'}
        self.assertTrue(predicate(record))
        self.assertFalse(predicate(dict(record, SYSLOG_IDENTIFIER='unrelated-app')))
        self.assertFalse(predicate(dict(record, MESSAGE='Preparing for sleep')))
        self.assertFalse(predicate({}))

    def test_recovery_and_blocker_ownership(self):
        # Run the production JS against a minimal Steam API. Existing blockers
        # belong to Steam/other clients and must survive our acquire/release.
        expression = next(n.value for n in ast.walk(TREE)
                          if isinstance(n, ast.Constant) and isinstance(n.value, str)
                          and n.value.startswith('(async () => {'))
        script = '''
const assert = require('node:assert/strict');
let calls = 0;
const store = {suspending:true, blockers:2,
 BlockSuspendAction(){this.blockers++; return ()=>this.blockers--;},
 InitiateResume(){calls++; this.suspending=false;}};
global.window = {SuspendResumeStore:store};
const source = SOURCE;
async function run(blocked,recover){
 return eval(source.replace('BLOCKED',String(blocked)).replace('RECOVER',String(recover)));
}
(async()=>{
 await run(true,false);
 assert.equal(store.suspending,true); assert.equal(calls,0);
 assert.equal(store.blockers,3);
 await run(true,true);
 assert.equal(calls,1); assert.equal(store.suspending,false);
 await run(true,true); assert.equal(calls,1);
 await run(false,false); assert.equal(store.blockers,2);
 // Failure is still recoverable if its short-lived inhibitor has already gone.
 store.suspending=true; await run(false,true);
 assert.equal(calls,2); assert.equal(store.blockers,2);
})().catch(e=>{console.error(e);process.exit(1)});
'''.replace('SOURCE', json.dumps(expression))
        subprocess.run(['node', '-e', script], check=True, timeout=5)


if __name__ == '__main__':
    unittest.main()
