export const emptyState=()=>({attempts:[],mastery:{},read:{},cardReviewed:{}});
export function validateCourses(courses){
 if(!Array.isArray(courses)||!courses.length||courses.length>100)throw Error('课程必须为1–100项的数组');
 const ids=new Set(); const str=(v)=>typeof v==='string'&&v.trim().length>0&&v.length<20000; const validId=v=>typeof v==='string'&&/^[a-zA-Z0-9_-]+$/.test(v);
 for(const c of courses){
  if(!str(c.id)||!/^[a-zA-Z0-9_-]+$/.test(c.id)||ids.has(c.id))throw Error('课程ID无效或重复');ids.add(c.id);
  if(!Number.isInteger(c.revision)||c.revision<1||!str(c.title)||!str(c.discipline)||c.confirmed!==true)throw Error('课程需有效版本、标题、学科及 confirmed:true');
  if(!Array.isArray(c.chapters)||!c.chapters.every(str)||!Array.isArray(c.nodes)||!c.nodes.length||!Array.isArray(c.questions)||!Array.isArray(c.sources))throw Error('课程结构不完整');
  const sources=new Map(c.sources.map(s=>[s.id,s]));if(sources.size!==c.sources.length||!c.sources.every(s=>str(s.id)&&str(s.title)&&Number.isInteger(s.pages)&&s.pages>0))throw Error('来源不完整或重复');
  const refs=(rs)=>{if(!Array.isArray(rs)||!rs.length)throw Error('缺少来源');for(const r of rs){const s=sources.get(r.sourceId);if(!s||!Array.isArray(r.pages)||!r.pages.length||!r.pages.every(p=>Number.isInteger(p)&&p>0&&p<=s.pages))throw Error('来源页码无效')}};
  const nodes=new Set();for(const n of c.nodes){if(!validId(n.id)||nodes.has(n.id)||!str(n.title)||!str(n.summary)||!c.chapters.includes(n.chapter)||!Array.isArray(n.rows)||!n.rows.every(r=>Array.isArray(r)&&r.length===2&&r.every(str))||!Array.isArray(n.framework)||!n.framework.every(str))throw Error('知识条目无效或重复');nodes.add(n.id);refs(n.sources)}
  const qs=new Set(),prompts=new Set();for(const q of c.questions){const canonical=String(q.prompt).replace(/[\s，。？！、：:,.!?]/g,'').toLowerCase();if(!validId(q.id)||qs.has(q.id)||prompts.has(canonical)||!str(q.prompt)||!nodes.has(q.nodeId))throw Error('题目重复或知识点关联无效');qs.add(q.id);prompts.add(canonical);if(q.type==='mcq'){if(!Array.isArray(q.options)||q.options.length!==4||new Set(q.options).size!==4||!q.options.every(str)||!Number.isInteger(q.answer)||q.answer<0||q.answer>3||!str(q.explanation))throw Error('单选题选项、答案或解析无效')}else if(q.type==='short'){if(!str(q.answerText))throw Error('简答题缺少参考要点')}else throw Error('不支持的题型');refs(q.sources)}
  if(c.questions.filter(q=>q.type==='mcq').length<100||!c.questions.some(q=>q.type==='short'))throw Error('每节需至少100道单选与简答题');
  if(!c.card||!str(c.card.id)||!Array.isArray(c.card.rows)||!c.card.rows.length||!c.card.rows.every(r=>str(r.label)&&str(r.text)&&nodes.has(r.nodeId)))throw Error('需一张有效课程卡片');
 }
 return courses;
}
export function validateState(s,courses){
 if(!s||!Array.isArray(s.attempts)||s.attempts.length>100000||!s.mastery||!s.read||!s.cardReviewed)throw Error('学习记录格式不正确');
 const byId=new Map(courses.map(c=>[c.id,c]));const seen=new Set();
 for(const a of s.attempts){const c=byId.get(a.courseId),q=c?.questions.find(q=>q.id===a.questionId);if(!q||typeof a.id!=='string'||seen.has(a.id)||typeof a.correct!=='boolean'||!Number.isFinite(a.at)||a.at<0||a.revision!==c.revision)throw Error('作答记录关联或版本无效');seen.add(a.id);if(q.type==='mcq'&&(!Number.isInteger(a.selected)||a.selected<0||a.selected>3||a.correct!==(a.selected===q.answer)))throw Error('作答选项与判分不一致');if(q.type==='short'&&(typeof a.text!=='string'||a.text.length>20000))throw Error('简答记录无效')}
 for(const [key,v] of Object.entries(s.mastery)){const [cid,nid]=key.split('/');if(!byId.get(cid)?.nodes.some(n=>n.id===nid)||!['unknown','learning','solid'].includes(v))throw Error('掌握度关联无效')}
 for(const [key,v] of Object.entries(s.read)){const [cid,nid]=key.split('/');if(!byId.get(cid)?.nodes.some(n=>n.id===nid)||typeof v!=='boolean')throw Error('阅读进度无效')}
 for(const [cid,v] of Object.entries(s.cardReviewed))if(!byId.has(cid)||!Number.isFinite(v))throw Error('卡片进度无效');
 return s;
}
export function latestAttempts(state,courseId){const m=new Map();for(const a of state.attempts)if(a.courseId===courseId&&(!m.has(a.questionId)||m.get(a.questionId).at<=a.at))m.set(a.questionId,a);return m}
export function mergeCourses(old,incoming){validateCourses(incoming);const m=new Map(old.map(c=>[c.id,c]));let added=0,updated=0,skipped=0;for(const c of incoming){const prev=m.get(c.id);if(!prev){m.set(c.id,c);added++}else if(c.revision>prev.revision){m.set(c.id,c);updated++}else if(c.revision===prev.revision&&JSON.stringify(c)!==JSON.stringify(prev)){throw Error(`课程 ${c.id} 同版本内容冲突，请提升 revision`)}else skipped++}return {courses:[...m.values()],added,updated,skipped}}
export function mergeStates(old,incoming,courses){const state=emptyState(),versions=new Map(courses.map(c=>[c.id,c.revision]));const attempts=new Map();for(const a of [...old.attempts,...incoming.attempts])if(versions.get(a.courseId)===a.revision){if(attempts.has(a.id)&&JSON.stringify(attempts.get(a.id))!==JSON.stringify(a))throw Error('作答ID冲突，未导入');attempts.set(a.id,a)}state.attempts=[...attempts.values()].sort((a,b)=>a.at-b.at);state.mastery={...old.mastery,...incoming.mastery};state.read={...old.read,...incoming.read};state.cardReviewed={...old.cardReviewed,...incoming.cardReviewed};validateState(state,courses);return state}
