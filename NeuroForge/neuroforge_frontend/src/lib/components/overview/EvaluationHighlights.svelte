<script lang="ts">
  import type { EvaluationSummary } from '$lib/types/overview';

  export let evaluationData: EvaluationSummary;

  function getTrendIndicator(trend: string): string {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    return '→';
  }

  function getScoreColor(score: number): string {
    if (score >= 0.9) return 'text-green-400';
    if (score >= 0.8) return 'text-yellow-400';
    return 'text-red-400';
  }
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
  <div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg p-6">
    <h3 class="text-lg font-semibold text-forge-ink-50 mb-4">Evaluation Summary</h3>

    <div class="space-y-4">
      <div class="bg-forge-ash-800 rounded-lg p-4">
        <p class="text-sm text-forge-ink-dim mb-2">Average Quality</p>
        <p class={`text-3xl font-bold ${getScoreColor(evaluationData.averageQuality)}`}>
          {(evaluationData.averageQuality * 100).toFixed(1)}%
        </p>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="bg-forge-ash-800 rounded-lg p-3">
          <p class="text-xs text-forge-ink-dim mb-1">Total Evaluations</p>
          <p class="text-2xl font-bold text-forge-ink-50">{evaluationData.totalEvaluations.toLocaleString()}</p>
        </div>

        <div class="bg-forge-ash-800 rounded-lg p-3">
          <p class="text-xs text-forge-ink-dim mb-1">Improvement Rate</p>
          <p class="text-2xl font-bold text-green-400">{evaluationData.improvementRate.toFixed(2)}%</p>
        </div>
      </div>
    </div>
  </div>

  <div class="bg-forge-ash-900 border border-forge-ash-700 rounded-lg overflow-hidden">
    <div class="px-6 py-4 border-b border-forge-ash-700 bg-forge-ash-800">
      <h3 class="text-lg font-semibold text-forge-ink-50">Top Models</h3>
    </div>

    <div class="p-6 space-y-4 max-h-72 overflow-y-auto">
      {#each evaluationData.topModels as model (model.modelId)}
        <div class="bg-forge-ash-800 rounded-lg p-4">
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="font-semibold text-forge-ink-50">{model.modelName}</p>
              <p class="text-xs text-forge-ink-dim">{model.domain}</p>
            </div>
            <div class="text-right">
              <p class={`text-lg font-bold ${getScoreColor(model.evaluationScore)}`}>
                {(model.evaluationScore * 100).toFixed(0)}%
              </p>
              <p class="text-lg">{getTrendIndicator(model.trend)}</p>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-2 text-xs">
            <div>
              <p class="text-forge-ink-dim">Coherence</p>
              <p class="text-forge-ink-50 font-semibold">{(model.coherenceScore * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p class="text-forge-ink-dim">Relevance</p>
              <p class="text-forge-ink-50 font-semibold">{(model.relevanceScore * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p class="text-forge-ink-dim">Factuality</p>
              <p class="text-forge-ink-50 font-semibold">{(model.factualityScore * 100).toFixed(0)}%</p>
            </div>
          </div>

          {#if model.improvement !== 0}
            <div class="mt-2 pt-2 border-t border-forge-ash-700">
              <p class="text-xs {model.trend === 'up' ? 'text-green-400' : 'text-red-400'}">
                {model.improvement > 0 ? '+' : ''}{model.improvement.toFixed(1)}% vs previous
              </p>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </div>
</div>
