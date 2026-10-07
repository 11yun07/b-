/* 评论互动散点图 + 高赞情绪判断 */
function _escSc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function initScatterChart(scatterId, verdictId, listId) {
  const chart = echarts.init(document.getElementById(scatterId));

  function render(data) {
    const sc = data.scatter || [];
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: (p) => `${p.data.name}<br/>点赞：${p.value[0]}　回复：${p.value[1]}`,
      },
      grid: { left: 50, right: 20, bottom: 40, top: 20 },
      xAxis: { type: 'value', name: '点赞数' },
      yAxis: { type: 'value', name: '回复数' },
      series: [{
        type: 'scatter',
        data: sc.map(s => ({ name: s.name, value: [s.like, s.reply] })),
        itemStyle: { color: '#1890ff', opacity: 0.6 },
      }],
    });

    const topLike = data.topLike || {};
    document.getElementById(verdictId).textContent = topLike.verdict || '';

    const list = document.getElementById(listId);
    const items = topLike.items || [];
    list.innerHTML = items.length
      ? items.map(t => `
        <li>
          <div class="t-user">${_escSc(t.user)}<span class="t-like">👍${t.like} [${t.label}]</span></div>
          <div class="t-content">${_escSc(t.content)}</div>
        </li>`).join('')
      : '<li class="empty">暂无热评</li>';
  }

  return { render, resize() { chart.resize(); } };
}
