import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateCourses,validateState,mergeCourses,mergeStates,emptyState} from '../model.js';
const read=async name=>JSON.parse(await readFile(new URL('../data/'+name,import.meta.url),'utf8'));
const {courses}=await read('courses.json');
const bundle=await read('sexually-transmitted-v1.json');
validateCourses(bundle.courses);
assert.deepEqual(Object.keys(bundle).sort(),['courses','kind','schemaVersion']);
assert.equal(bundle.kind,'medical-review-content');
assert.equal(bundle.courses.length,1);
const c=bundle.courses[0];
assert.equal(c.id,'derm-sexually-transmitted');
assert.equal(c.revision,1);
assert.deepEqual(courses.find(x=>x.id===c.id),c);
assert.equal(c.nodes.length,18);
assert.equal(c.card.rows.length,11);
assert.ok(c.nodes.every(n=>n.weak===false));
assert.ok(c.card.rows.every(r=>!r.label.includes('★')));
const mc=c.questions.filter(q=>q.type==='mcq');
assert.equal(mc.length,100);
assert.equal(c.questions.filter(q=>q.type==='short').length,12);
assert.equal(new Set(mc.map(q=>q.objective)).size,100);
for(let i=0;i<4;i++)assert.equal(mc.filter(q=>q.answer===i).length,25);
const privateFields=new Set(['attempts','state','userAnswer','userAnswerVerbatim','results','mastery','archivedOn','selected','score','exportedAt']);
function publicOnly(value){
 if(Array.isArray(value))value.forEach(publicOnly);
 else if(value&&typeof value==='object')for(const [key,v]of Object.entries(value)){
  assert.ok(!privateFields.has(key),`Private field ${key}`);publicOnly(v);
 }
}
publicOnly(bundle);
for(const row of c.card.rows){
 assert.ok(c.nodes.some(n=>n.id===row.nodeId));
 for(const ref of row.sources){
  const source=c.sources.find(s=>s.id===ref.sourceId);assert.ok(source);
  assert.ok(ref.pages.length&&ref.pages.every(p=>Number.isInteger(p)&&p>0&&p<=source.pages));
 }
}
const old=courses.filter(x=>x.id!==c.id);
const added=mergeCourses(old,bundle.courses);
assert.equal(added.added,1);assert.deepEqual(added.courses,courses);
assert.equal(mergeCourses(courses,bundle.courses).skipped,1);
const state=emptyState();
for(const other of old){
 const q=other.questions.find(q=>q.type==='mcq');
 state.attempts.push({id:`synthetic-${other.id}`,courseId:other.id,questionId:q.id,revision:other.revision,selected:q.answer,correct:true,at:1});
 state.read[`${other.id}/${other.nodes[0].id}`]=true;
}
validateState(state,courses);
assert.deepEqual(mergeStates(state,emptyState(),added.courses),state);
const both=structuredClone(state);
both.attempts.push({id:'synthetic-sti',courseId:c.id,questionId:mc[0].id,revision:1,selected:mc[0].answer,correct:true,at:2});
const revised=structuredClone(bundle.courses);revised[0].revision=2;
const upgraded=mergeCourses(courses,revised).courses;
assert.deepEqual(mergeStates(both,emptyState(),upgraded),state);
assert.equal(mergeCourses(upgraded,bundle.courses).skipped,1);
const conflict=structuredClone(bundle.courses);conflict[0].questions[0].prompt+='内容修改';
assert.throws(()=>mergeCourses(courses,conflict),/同版本内容冲突/);
console.log('PASS: STI v1, 18 nodes, 100 distinct objectives, 12 short, one 11-row card, balanced answers, public fields/sources, additive import, prior history preservation and revision isolation');
