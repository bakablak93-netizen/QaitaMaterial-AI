import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
const source = await readFile(new URL('../src/workflows.ts', import.meta.url), 'utf8');
const {outputText} = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}});
const {loadAllPages} = await import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));

for (const count of [0, 100, 105, 250]) {
  test(`catalogue loads all ${count} materials, including older search results`, async () => {
    const data = Array.from({length: count}, (_, id) => ({id, name: `Material ${id}`}));
    const result = await loadAllPages(async (offset, limit) => data.slice(offset, offset + limit));
    assert.deepEqual(result, data);
    if (count > 100) assert.equal(result.find(row => row.name === 'Material 104').id, 104);
  });
}
test('page failure is reported instead of returning an incomplete catalogue', async () => {
  await assert.rejects(loadAllPages(async offset => {
    if (offset) throw new Error('Connection failed');
    return Array(100).fill({id: 1});
  }), /Connection failed/);
});
