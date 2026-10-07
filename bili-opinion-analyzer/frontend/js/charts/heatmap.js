/* 弹幕视频内时间热力图（X=视频时间分钟，Y=日期） */
function initHeatmapChart(domId) {
  const chart = echarts.init(document.getElementById(domId));

  function render(data) {
    const h = data.heatmap || {};
    if (h.x && h.x.length) {
      const max = Math.max(1, ...h.data.map(d => d[2]));
      chart.setOption({
        tooltip: { position: 'top', formatter: (p) => `${h.y[p.value[1]]}<br/>${h.x[p.value[0]]}: ${p.value[2]} 条` },
        grid: { left: 90, right: 20, bottom: 60, top: 10, containLabel: false },
        xAxis: { type: 'category', data: h.x, name: '视频内时间', splitArea: { show: true } },
        yAxis: { type: 'category', data: h.y, name: '日期', splitArea: { show: true } },
        visualMap: {
          min: 0, max, calculable: true, orient: 'horizontal',
          left: 'center', bottom: 0,
          inRange: { color: ['#e6f4ff', '#91caff', '#1890ff', '#003a8c'] },
        },
        series: [{
          type: 'heatmap', data: h.data, label: { show: false },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
        }],
      });
    } else {
      chart.setOption({ title: { text: '暂无弹幕数据', left: 'center', top: 'center' } });
    }
  }

  return { render, resize() { chart.resize(); } };
}
