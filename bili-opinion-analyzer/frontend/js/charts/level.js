/* 用户等级分布柱状图（评论 vs 弹幕） */
function initLevelChart(domId) {
  const chart = echarts.init(document.getElementById(domId));

  function render(data) {
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['评论用户', '弹幕用户'] },
      grid: { left: 40, right: 20, bottom: 30, top: 40 },
      xAxis: { type: 'category', data: data.categories },
      yAxis: { type: 'value' },
      series: [
        { name: '评论用户', type: 'bar', data: data.comments, itemStyle: { color: '#1890ff' } },
        { name: '弹幕用户', type: 'bar', data: data.danmakus, itemStyle: { color: '#fa8c16' } },
      ],
    });
  }

  return { render, resize() { chart.resize(); } };
}
