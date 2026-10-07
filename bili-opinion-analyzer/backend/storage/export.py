# -*- coding: utf-8 -*-
"""导出 CSV / JSON / SQLite，以及生成 HTML 舆情报告。"""
import csv
import json
import os
import time

from backend import config
from backend.storage import db


def _path(kind, ext):
    ts = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(config.EXPORT_DIR, f"{kind}_{ts}.{ext}")


def _rows_for_csv(rows):
    out = []
    for r in rows:
        d = dict(r)
        for k, v in d.items():
            if isinstance(v, (list, dict)):
                d[k] = json.dumps(v, ensure_ascii=False)
        out.append(d)
    return out


def to_csv(rows, kind):
    path = _path(kind, "csv")
    fieldnames = list(rows[0].keys()) if rows else ["(empty)"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in _rows_for_csv(rows):
            writer.writerow(r)
    return path


def to_json(rows, kind):
    path = _path(kind, "json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return path


def to_sqlite(rows, kind):
    if kind == "comments":
        db.save_comments(rows)
    elif kind == "danmakus":
        db.save_danmakus(rows)
    else:
        raise ValueError(f"未知数据类型：{kind}")
    return config.DB_PATH


# --------------------------------------------------------------------------- #
# 一键生成 HTML 舆情报告
# --------------------------------------------------------------------------- #
def build_report_html(data):
    """生成自包含的 HTML 报告文件（内嵌数据 + CDN echarts），返回文件路径。"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(config.EXPORT_DIR, f"report_{ts}.html")
    payload = json.dumps(data, ensure_ascii=False)
    html = _REPORT_TEMPLATE.replace("__DATA__", payload)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


_REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>B站舆论分析报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root{--bg:#f6f7fb;--card:#fff;--border:#e8eaf0;--text:#1a1d24;--muted:#6b7280;--pos:#22c55e;--neg:#ef4444;--neu:#3b82f6;--radius:14px;--shadow:0 1px 2px rgba(16,24,40,.04)}
@media (prefers-color-scheme: dark){:root{--bg:#0f1115;--card:#171a21;--border:#272b36;--text:#e7eaf0;--muted:#8b93a1;--shadow:0 1px 2px rgba(0,0,0,.4)}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.65;padding:28px 20px}
.wrap{max-width:1080px;margin:0 auto}
header.report-head{margin-bottom:18px}
header.report-head h1{font-size:26px;font-weight:700;letter-spacing:-.5px}
header.report-head .sub{color:var(--muted);font-size:13px;margin-top:4px}
.print-btn{position:fixed;top:18px;right:18px;z-index:10;border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:8px;padding:8px 14px;font-size:13px;cursor:pointer;box-shadow:var(--shadow)}
.bento{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:18px;box-shadow:var(--shadow)}
.card h2{font-size:15px;font-weight:600;margin-bottom:12px}
.card h2 .hint{font-size:12px;color:var(--muted);font-weight:400}
.col-3{grid-column:span 3}.col-5{grid-column:span 5}.col-6{grid-column:span 6}.col-7{grid-column:span 7}.col-9{grid-column:span 9}.col-12{grid-column:span 12}
.chart{width:100%;height:280px}
.hidden{display:none}
/* 健康度 */
.health{display:flex;gap:16px;align-items:center;height:100%}
.health .gauge{width:150px;height:150px;flex-shrink:0}
.health .meta{flex:1}
.health .level{font-size:16px;font-weight:700;margin-bottom:6px}
.health .desc{font-size:12px;color:var(--muted);line-height:1.6}
/* 关键发现 */
.insights{list-style:none}
.insights li{position:relative;padding:10px 0 10px 26px;border-bottom:1px dashed var(--border);font-size:14px}
.insights li:last-child{border-bottom:none}
.insights li::before{content:'';position:absolute;left:6px;top:17px;width:8px;height:8px;border-radius:50%;background:var(--neu)}
.insights li.neg::before{background:var(--neg)}
.insights li.pos::before{background:var(--pos)}
/* 指标卡 */
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;text-align:center}
.stat .n{font-size:24px;font-weight:700;line-height:1.2}
.stat .l{font-size:12px;color:var(--muted);margin-top:2px}
/* 表格 */
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:middle}
th{background:var(--bg);color:var(--muted);font-weight:600;font-size:12px}
.bar{height:8px;border-radius:4px;background:var(--border);overflow:hidden;display:inline-block;width:100%;min-width:80px}
.bar .fill{height:100%;float:left}
.fill.pos{background:var(--pos)}.fill.neg{background:var(--neg)}.fill.neu{background:var(--neu)}
/* 高赞评论 */
.filters{display:flex;gap:8px;margin-bottom:10px}
.filters button{border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:6px;padding:4px 12px;font-size:12px;cursor:pointer}
.filters button.active{background:var(--neu);color:#fff;border-color:var(--neu)}
.like-list{list-style:none}
.like-list li{display:flex;gap:10px;padding:10px 0;border-bottom:1px dashed var(--border);align-items:flex-start}
.like-list .dot{width:9px;height:9px;border-radius:50%;margin-top:6px;flex-shrink:0}
.like-list .body{flex:1;min-width:0}
.like-list .content{font-size:14px;margin:2px 0}
.like-list .meta{font-size:12px;color:var(--muted)}
.like-bar{height:6px;border-radius:3px;background:var(--border);margin-top:4px;max-width:260px}
.like-bar .fill{height:100%;border-radius:3px;background:var(--neu)}
/* 聚类 */
.cluster{margin-bottom:14px}
.cluster .head{font-weight:600;font-size:14px;margin-bottom:4px}
.tag{display:inline-block;background:rgba(59,130,246,.12);color:var(--neu);border-radius:5px;padding:1px 8px;font-size:12px;margin:2px}
.cluster .samples{font-size:12px;color:var(--muted);margin-top:4px}
.cluster .samples div{margin:2px 0}
.foot{color:var(--muted);font-size:12px;margin-top:20px;line-height:1.7}
@media (max-width:820px){.col-3,.col-5,.col-6,.col-7,.col-9{grid-column:span 12}.stats{grid-template-columns:repeat(2,1fr)}}
@media print{body{background:#fff;padding:0}.card{box-shadow:none;break-inside:avoid}.no-print{display:none!important}}
</style>
</head>
<body>
<div class="wrap">
<header class="report-head">
  <h1>📊 B站舆论分析报告</h1>
  <div class="sub" id="sub"></div>
  <button class="print-btn no-print" onclick="window.print()">🖨️ 打印 / 另存为 PDF</button>
</header>

<div class="stats" id="stats"></div>

<div class="bento">
  <div class="card col-3">
    <h2>舆情健康度</h2>
    <div class="health">
      <div class="gauge" id="gauge"></div>
      <div class="meta"><div class="level" id="level"></div><div class="desc" id="level-desc"></div></div>
    </div>
  </div>
  <div class="card col-9">
    <h2>关键发现</h2>
    <ul class="insights" id="insights"></ul>
  </div>

  <div class="card col-5"><h2>情感分布</h2><div class="chart" id="pie"></div></div>
  <div class="card col-7"><h2>情感趋势 <span class="hint">柱=评论数 · 线=情感均值</span></h2><div class="chart" id="trend"></div></div>
  <div class="card col-6" id="op-pos-card"><h2>👍 大家在夸什么</h2><div class="chart" id="bar-pos"></div></div>
  <div class="card col-6" id="op-neg-card"><h2>👎 大家在骂什么</h2><div class="chart" id="bar-neg"></div></div>

  <div class="card col-6" id="hl-card"><h2>🎬 名场面 / 高能时刻</h2><table><thead><tr><th>时间段</th><th>弹幕数</th><th>代表弹幕</th></tr></thead><tbody id="hl"></tbody></table></div>
  <div class="card col-6" id="cluster-card"><h2>🧠 观点聚类</h2><div id="clusters"></div></div>
  <div class="card col-12" id="pk-card"><h2>🏆 跨视频 PK 榜</h2><table><thead><tr><th>视频</th><th>评论数</th><th>情感均值</th><th>正面 vs 负面</th><th>均赞</th><th>争议度</th></tr></thead><tbody id="pk"></tbody></table></div>
  <div class="card col-12" id="like-card"><h2>🔥 高赞评论情绪 <span class="hint">判断高赞=认同还是群嘲</span></h2><div class="filters" id="filters"></div><ul class="like-list" id="likelist"></ul></div>
</div>

<div class="foot" id="foot"></div>
</div>

<script>
var DATA = __DATA__;
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function pct(x,t){return Math.round((x/(t||1))*100)}
var st = DATA.stats, total = (st.positive+st.negative+st.neutral)||1;

document.getElementById('sub').textContent = '生成时间：' + DATA.generated_at + '　｜　样本：评论 ' + st.comments + ' 条 · 弹幕 ' + st.danmakus + ' 条 · 视频 ' + st.videos + ' 个';

document.getElementById('stats').innerHTML =
  '<div class="stat"><div class="n" style="color:#22c55e">'+st.positive+'</div><div class="l">正面</div></div>'+
  '<div class="stat"><div class="n" style="color:#3b82f6">'+st.neutral+'</div><div class="l">中性</div></div>'+
  '<div class="stat"><div class="n" style="color:#ef4444">'+st.negative+'</div><div class="l">负面</div></div>'+
  '<div class="stat"><div class="n">'+st.comments+'</div><div class="l">评论数</div></div>'+
  '<div class="stat"><div class="n">'+st.danmakus+'</div><div class="l">弹幕数</div></div>';

/* 健康度仪表盘 */
var h = DATA.health||{}, hc = h.color||'#3b82f6';
var gauge = echarts.init(document.getElementById('gauge'));
gauge.setOption({series:[{type:'gauge',startAngle:210,endAngle:-30,min:0,max:100,radius:'95%',center:['50%','60%'],
  progress:{show:true,width:14,itemStyle:{color:hc}},
  axisLine:{lineStyle:{width:14,color:[[1,'#e5e7eb']]}},
  axisTick:{show:false},splitLine:{show:false},axisLabel:{show:false},pointer:{show:false},anchor:{show:false},
  detail:{valueAnimation:true,fontSize:34,fontWeight:700,offsetCenter:[0,'0%'],formatter:'{value}',color:hc},
  data:[{value:h.score||0}]}]});
document.getElementById('level').textContent = (h.level||'') + ' · 健康分 ' + (h.score||0);
document.getElementById('level').style.color = hc;
document.getElementById('level-desc').textContent = '情感均值 ' + (h.avg_score||0) + '（0~1 越高越正面），负评占比 ' + pct(st.negative,total) + '%。';

/* 关键发现 */
document.getElementById('insights').innerHTML = (DATA.insights||[]).map(function(s){
  var cls = '';
  if(s.indexOf('负面')>=0 && s.indexOf('正面')<0) cls=' class="neg"';
  else if(s.indexOf('正面')>=0 && s.indexOf('负面')<0) cls=' class="pos"';
  return '<li'+cls+'>'+esc(s)+'</li>';
}).join('') || '<li>暂无</li>';

/* 情感环形图 + 中心数字 */
var pie = echarts.init(document.getElementById('pie'));
pie.setOption({tooltip:{trigger:'item'},legend:{bottom:0},
  graphic:[{type:'text',left:'center',top:'40%',style:{text:String(total),fontSize:30,fontWeight:700,fill:'#555'}}],
  series:[{type:'pie',radius:['52%','72%'],center:['50%','46%'],label:{show:false},data:[
    {name:'正面',value:st.positive,itemStyle:{color:'#22c55e'}},
    {name:'中性',value:st.neutral,itemStyle:{color:'#3b82f6'}},
    {name:'负面',value:st.negative,itemStyle:{color:'#ef4444'}}]}]});

/* 情感趋势 + 面积渐变 */
var tl = DATA.trend||[];
var trend = echarts.init(document.getElementById('trend'));
trend.setOption({tooltip:{trigger:'axis'},legend:{data:['评论数','情感均值']},
  grid:{left:45,right:45,bottom:45,top:30},
  xAxis:{type:'category',data:tl.map(function(t){return t.time}),axisLabel:{rotate:30,color:'#888'}},
  yAxis:[{type:'value',name:'评论数',axisLabel:{color:'#888'}},{type:'value',name:'情感均值',min:0,max:1,axisLabel:{color:'#888'}}],
  series:[
    {name:'评论数',type:'bar',data:tl.map(function(t){return t.count}),itemStyle:{color:'#3b82f6',opacity:.55}},
    {name:'情感均值',type:'line',yAxisIndex:1,smooth:true,data:tl.map(function(t){return t.avg_score}),
     lineStyle:{color:'#f59e0b',width:3},itemStyle:{color:'#f59e0b'},
     areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(245,158,11,.25)'},{offset:1,color:'rgba(245,158,11,0)'}]}}}
  ]});

/* 夸/骂横向条形图 */
function hbar(cardId, domId, words, color){
  var w = (words||[]).slice(0,12).reverse();
  if(!w.length){ document.getElementById(cardId).classList.add('hidden'); return; }
  var chart = echarts.init(document.getElementById(domId));
  chart.setOption({grid:{left:90,right:20,top:10,bottom:20},
    xAxis:{type:'value',axisLabel:{color:'#888'}},
    yAxis:{type:'category',data:w.map(function(x){return x.name}),axisLabel:{color:'#555'}},
    series:[{type:'bar',data:w.map(function(x){return x.value}),barWidth:14,itemStyle:{color:color,borderRadius:[0,4,4,0]}}]});
}
hbar('op-pos-card','bar-pos',(DATA.opinion||{}).positive,'#22c55e');
hbar('op-neg-card','bar-neg',(DATA.opinion||{}).negative,'#ef4444');

/* 名场面（空则隐藏） */
var hl = DATA.highlights||[];
if(!hl.length){ document.getElementById('hl-card').classList.add('hidden'); }
else document.getElementById('hl').innerHTML = hl.map(function(h){
  return '<tr><td>'+h.start+' ~ '+h.end+'</td><td>'+h.count+'</td><td>'+h.samples.map(esc).join('、')+'</td></tr>';
}).join('');

/* 观点聚类（空则隐藏） */
var cls = (DATA.clusters||{}).clusters||[];
if(!cls.length){ document.getElementById('cluster-card').classList.add('hidden'); }
else document.getElementById('clusters').innerHTML = cls.map(function(c){
  return '<div class="cluster"><div class="head">观点'+c.id+' <span style="color:#888;font-weight:400">（'+Math.round(c.ratio*100)+'% · '+c.size+'条）</span></div>'+
    c.keywords.map(function(k){return '<span class="tag">'+esc(k)+'</span>'}).join('')+
    '<div class="samples">'+c.samples.map(function(s){return '<div>· '+esc(s)+'</div>'}).join('')+'</div></div>';
}).join('');

/* PK 榜 + 内嵌堆叠条（空则隐藏） */
var cp = DATA.compare||[];
if(!cp.length){ document.getElementById('pk-card').classList.add('hidden'); }
else document.getElementById('pk').innerHTML = cp.map(function(v){
  var pp=Math.round(v.positive_ratio*100), np=Math.round(v.negative_ratio*100), mp=100-pp-np;
  var sc = v.avg_score>=0.6?'#22c55e':(v.avg_score<=0.4?'#ef4444':'#f59e0b');
  return '<tr><td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(v.title)+'</td>'+
    '<td>'+v.comment_count+'</td><td style="color:'+sc+';font-weight:700">'+v.avg_score+'</td>'+
    '<td><div class="bar"><div class="fill pos" style="width:'+pp+'%"></div><div class="fill neu" style="width:'+mp+'%"></div><div class="fill neg" style="width:'+np+'%"></div></div><div style="font-size:11px;color:#888">正'+pp+'% · 负'+np+'%</div></td>'+
    '<td>'+v.avg_like+'</td><td>'+v.controversy+'</td></tr>';
}).join('');

/* 高赞评论 + 情感筛选 */
var likeItems = (DATA.top_like||{}).items||[];
var filters = document.getElementById('filters');
function drawLikes(filter){
  var items = likeItems;
  if(filter && filter!=='all') items = likeItems.filter(function(i){return i.label===filter});
  var maxLike = Math.max.apply(null, likeItems.map(function(i){return i.like}).concat([1]));
  document.getElementById('likelist').innerHTML = items.length ? items.map(function(i){
    var color = i.label==='正面'?'#22c55e':(i.label==='负面'?'#ef4444':'#3b82f6');
    return '<li><span class="dot" style="background:'+color+'"></span><div class="body">'+
      '<div class="content">'+esc(i.content)+'</div>'+
      '<div class="meta">'+esc(i.user)+' · 👍 '+i.like+' · '+i.label+'</div>'+
      '<div class="like-bar"><div class="fill" style="width:'+(i.like/maxLike*100)+'%"></div></div></div></li>';
  }).join('') : '<li style="color:#888">无匹配评论</li>';
}
if(likeItems.length){
  var labels=['全部','正面','中性','负面'];
  filters.innerHTML = labels.map(function(l){var k=l==='全部'?'all':l;return '<button data-f="'+k+'" class="'+(l==='全部'?'active':'')+'">'+l+'</button>'}).join('');
  filters.addEventListener('click',function(e){if(e.target.tagName!=='BUTTON')return;filters.querySelectorAll('button').forEach(function(b){b.classList.remove('active')});e.target.classList.add('active');drawLikes(e.target.getAttribute('data-f'))});
  drawLikes('all');
}else document.getElementById('like-card').classList.add('hidden');

/* 方法论脚注 */
document.getElementById('foot').innerHTML = '<b>方法论说明</b>：本报告由「B站舆论分析工具」自动生成，数据来自 B 站公开评论与弹幕接口（无登录态采集）。情感分析基于 SnowNLP（0~1，≥0.6 正面、≤0.4 负面、其余中性）；词频基于 jieba + TF-IDF；观点聚类为 TF-IDF + KMeans。结果仅供个人学习研究参考，不代表官方立场。';
</script>
</body>
</html>
"""
