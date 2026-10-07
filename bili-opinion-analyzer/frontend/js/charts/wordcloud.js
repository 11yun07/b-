/* 评论/弹幕词云 */
function _randomColor() {
  const colors = ['#1890ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1', '#13c2c2', '#f5222d', '#2f54eb'];
  return colors[Math.floor(Math.random() * colors.length)];
}

function initWordcloudChart(commentId, danmakuId) {
  const c = echarts.init(document.getElementById(commentId));
  const d = echarts.init(document.getElementById(danmakuId));

  function option(words) {
    return {
      tooltip: { show: true },
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        left: 'center', top: 'center', width: '92%', height: '92%',
        sizeRange: [12, 60], rotationRange: [0, 0], gridSize: 6,
        textStyle: { color: () => _randomColor() },
        emphasis: { textStyle: { color: '#000' } },
        data: (words || []).map(w => ({ name: w.name, value: w.value })),
      }],
    };
  }

  function render(data) {
    c.setOption(option(data.comment));
    d.setOption(option(data.danmaku));
  }

  return { render, resize() { c.resize(); d.resize(); } };
}
