/* 跨视频 PK 榜（纯 DOM 表格） */
function _escCp(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function initComparePanel(tableId) {
  function render(data) {
    const el = document.getElementById(tableId);
    const rows = data.videos || [];
    el.innerHTML = rows.length
      ? rows.map(v => `
        <tr>
          <td class="title">${_escCp(v.title)}</td>
          <td>${v.comment_count}</td>
          <td>${v.avg_score}</td>
          <td>${Math.round(v.positive_ratio * 100)}%</td>
          <td>${Math.round(v.negative_ratio * 100)}%</td>
          <td>${v.avg_like}</td>
          <td>${v.controversy}</td>
        </tr>`).join('')
      : '<tr><td colspan="7" class="empty">暂无评论数据（需重新采集以带视频归属）</td></tr>';
  }
  return { render, resize() {} };
}
