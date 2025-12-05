<script lang="ts">
  import { onMount } from 'svelte';
  import { Chart, registerables } from 'chart.js';

  Chart.register(...registerables);

  export let title: string = '';
  export let labels: string[] = [];
  export let data: number[] = [];
  export let color: string = '#00A3FF';
  export let yAxisLabel: string = '';
  export let xAxisLabel: string = 'Time';

  let canvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  onMount(() => {
    if (canvas) {
      chart = new Chart(canvas, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: title,
            data: data,
            borderColor: color,
            backgroundColor: color + '20',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: color,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 1,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              backgroundColor: '#1A1A1D',
              titleColor: '#FFFFFF',
              bodyColor: '#FFFFFF',
              borderColor: '#4A4A4F',
              borderWidth: 1,
              padding: 10,
              displayColors: false,
            }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: xAxisLabel,
                color: '#A0A0A5'
              },
              ticks: {
                color: '#A0A0A5',
                maxRotation: 45,
                minRotation: 45
              },
              grid: {
                color: '#2A2A2F',
                drawBorder: false
              }
            },
            y: {
              title: {
                display: true,
                text: yAxisLabel,
                color: '#A0A0A5'
              },
              ticks: {
                color: '#A0A0A5'
              },
              grid: {
                color: '#2A2A2F',
                drawBorder: false
              },
              beginAtZero: true
            }
          }
        }
      });
    }

    return () => {
      if (chart) {
        chart.destroy();
      }
    };
  });

  // Update chart when data changes
  $: if (chart) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update();
  }
</script>

<div class="chart-container">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .chart-container {
    position: relative;
    height: 300px;
    width: 100%;
  }
</style>
