/* 情感分布环形图 + 情感趋势折线图 */
function initSentimentChart(pieId, lineId) {
  const pie = echarts.init(document.getElementById(pieId));
  const line = echarts.init(document.getElementById(lineId));

  function render(data) {
    const dist = data.distribution || {};
    pie.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '68%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%' },
        data: [
          { name: '正面', value: dist.positive || 0, itemStyle: { color: '#52c41a' } },
          { name: '中性', value: dist.neutral || 0, itemStyle: { color: '#1890ff' } },
          { name: '负面', value: dist.negative || 0, itemStyle: { color: '#ff4d4f' } },
        ],
      }],
    });

    const trend = data.trend || [];
    line.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['评论数', '情感均值'] },
      grid: { left: 40, right: 40, bottom: 50, top: 30 },
      xAxis: { type: 'category', data: trend.map(t => t.time), axisLabel: { rotate: 30 } },
      yAxis: [
        { type: 'value', name: '评论数' },
        { type: 'value', name: '情感均值', min: 0, max: 1 },
      ],
      series: [
        { name: '评论数', type: 'bar', data: trend.map(t => t.count), itemStyle: { color: '#91caff' } },
        { name: '情感均值', type: 'line', yAxisIndex: 1, smooth: true, data: trend.map(t => t.avg_score), itemStyle: { color: '#fa8c16' } },
      ],
    });
  }

  return { render, resize() { pie.resize(); line.resize(); } };
}
