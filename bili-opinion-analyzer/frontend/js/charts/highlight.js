/* 名场面 / 高能时刻列表（纯 DOM） */
function _escHl(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function initHighlightPanel(listId) {
  function render(data) {
    const el = document.getElementById(listId);
    const hl = data.highlights || [];
    el.innerHTML = hl.length
      ? hl.map(h => `<li><b>${h.start} ~ ${h.end}</b>（${h.count} 条）<div class="hl-samples">${h.samples.map(_escHl).join('、')}</div></li>`).join('')
      : '<li class="empty">暂无弹幕数据</li>';
  }
  return { render, resize() {} };
}
