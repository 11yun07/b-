/* 「夸什么 vs 骂什么」双词云 */
function initOpinionChart(posId, negId) {
  const p = echarts.init(document.getElementById(posId));
  const n = echarts.init(document.getElementById(negId));

  function option(words, color) {
    return {
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        left: 'center', top: 'center', width: '92%', height: '92%',
        sizeRange: [12, 55], rotationRange: [0, 0], gridSize: 6,
        textStyle: { color: () => color },
        emphasis: { textStyle: { color: '#000' } },
        data: (words || []).map(w => ({ name: w.name, value: w.value })),
      }],
    };
  }

  function render(data) {
    p.setOption(option(data.positive, '#52c41a'));
    n.setOption(option(data.negative, '#ff4d4f'));
  }

  return { render, resize() { p.resize(); n.resize(); } };
}
