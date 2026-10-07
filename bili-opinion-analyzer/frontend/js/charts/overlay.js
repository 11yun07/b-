/* 弹幕密度 × 情感均值叠加曲线（视频内时间轴） */
function initOverlayChart(domId) {
  const chart = echarts.init(document.getElementById(domId));

  function render(data) {
    const buckets = data.buckets || [];
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['弹幕密度', '情感均值'] },
      grid: { left: 50, right: 50, bottom: 40, top: 30 },
      xAxis: { type: 'category', data: buckets.map(b => b.label) },
      yAxis: [
        { type: 'value', name: '弹幕数' },
        { type: 'value', name: '情感均值', min: 0, max: 1 },
      ],
      series: [
        { name: '弹幕密度', type: 'bar', data: buckets.map(b => b.count), itemStyle: { color: '#91caff' } },
        { name: '情感均值', type: 'line', yAxisIndex: 1, smooth: true, data: buckets.map(b => b.avg_score), itemStyle: { color: '#fa8c16' } },
      ],
    });
  }

  return { render, resize() { chart.resize(); } };
}
