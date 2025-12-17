<template>
  <div class="graph-container">
    <div class="graph-header">
      <h3>Graph Visualization</h3>
      <div class="graph-controls">
        <input
          v-model="customQuery"
          type="text"
          placeholder="MATCH (n) RETURN n"
          class="graph-query-input"
          :disabled="isLocked"
          @input="onQueryInput"
        />
        <button 
          @click="toggleLock" 
          :class="['btn', 'btn-small', 'lock-btn', { locked: isLocked }]"
          :title="isLocked ? 'Unlock to edit query' : 'Lock to enable auto-execution'"
        >
          <span class="lock-icon">{{ isLocked ? '🔒' : '🔓' }}</span>
          <span class="lock-text">{{ isLocked ? 'Locked' : 'Unlocked' }}</span>
        </button>
      </div>
    </div>
    <div ref="graphContainer" class="graph-visualization"></div>
    <div v-if="error" class="graph-error">{{ error }}</div>
    <div v-if="noResults && !error" class="graph-no-results">
      <div class="no-results-icon">📊</div>
      <div class="no-results-message">
        <h4>No Results Found</h4>
        <p>The query returned no nodes or edges. Try modifying your query or check if the graph contains data.</p>
      </div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import axios from 'axios'

export default {
  name: 'GraphVisualization',
  data() {
    return {
      chart: null,
      isLocked: true,  // When locked, auto-executes and input is disabled
      customQuery: 'MATCH (n) RETURN n',
      currentQuery: 'MATCH (n) RETURN n',
      refreshInterval: null,
      error: null,
      noResults: false,
      queryDebounceTimer: null,
      lastResultHash: null
    }
  },
  mounted() {
    // Wait for DOM to be fully ready
    this.$nextTick(() => {
      this.initializeGraph()
      // Start auto-refresh if locked (locked = auto-execute enabled)
      if (this.isLocked) {
        this.startAutoRefresh()
      }
    })
  },
  beforeUnmount() {
    this.stopAutoRefresh()
    if (this.chart) {
      this.chart.dispose()
      this.chart = null
    }
  },
  methods: {
    async initializeGraph() {
      try {
        // Check if component is still mounted
        if (!this.$el) return
        
        const dataUpdated = await this.fetchGraphData()
        if (dataUpdated) {
          this.$nextTick(() => {
            if (this.$el) {
              this.renderGraph()
            }
          })
        }
      } catch (error) {
        console.error('Error initializing graph:', error)
        this.error = error.response?.data?.detail || error.message || 'Failed to initialize graph visualization'
      }
    },
    async fetchGraphData() {
      try {
        this.error = null
        const response = await axios.post('/api/graph/query', {
          query: this.currentQuery
        })
        
        const data = response.data
        
        // Log the data received from backend
        console.log('Graph query response:', {
          query: this.currentQuery,
          nodes: data.nodes || [],
          edges: data.edges || [],
          nodeCount: (data.nodes || []).length,
          edgeCount: (data.edges || []).length
        })
        console.log('Sample nodes:', (data.nodes || []).slice(0, 3))
        console.log('Sample edges:', (data.edges || []).slice(0, 3))
        
        // Calculate hash of the result
        const resultHash = this.calculateResultHash(data.nodes || [], data.edges || [])
        
        // Only update if hash changed
        if (resultHash === this.lastResultHash) {
          return false // No change, skip rendering
        }
        
        this.lastResultHash = resultHash
        
        // Store data for rendering
        this.graphData = {
          nodes: data.nodes || [],
          edges: data.edges || []
        }
        
        // Check if there are no results
        if ((!this.graphData.nodes || this.graphData.nodes.length === 0) && 
            (!this.graphData.edges || this.graphData.edges.length === 0)) {
          this.noResults = true
        } else {
          this.noResults = false
        }
        
        return true // Data was updated
      } catch (error) {
        console.error('Error fetching graph data:', error)
        this.error = error.response?.data?.detail || error.message || 'Failed to fetch graph data'
        this.noResults = false
        throw error
      }
    },
    calculateResultHash(nodes, edges) {
      // Create a simple hash by stringifying and hashing the sorted data
      // Sort nodes and edges by ID for consistent hashing
      const sortedNodes = [...nodes].sort((a, b) => (a.id || '').localeCompare(b.id || ''))
      const sortedEdges = [...edges].sort((a, b) => {
        const aKey = `${a.source}-${a.target}-${a.label || ''}`
        const bKey = `${b.source}-${b.target}-${b.label || ''}`
        return aKey.localeCompare(bKey)
      })
      
      const dataString = JSON.stringify({ nodes: sortedNodes, edges: sortedEdges })
      
      // Simple hash function
      let hash = 0
      for (let i = 0; i < dataString.length; i++) {
        const char = dataString.charCodeAt(i)
        hash = ((hash << 5) - hash) + char
        hash = hash & hash // Convert to 32-bit integer
      }
      return hash.toString()
    },
    renderGraph() {
      if (!this.graphData || !this.graphData.nodes || !this.graphData.edges) {
        // If no data, don't render but keep the no-results message visible
        if (this.chart) {
          this.chart.dispose()
          this.chart = null
        }
        return
      }
      
      // If we have data, clear the no-results flag
      if (this.graphData.nodes.length > 0 || this.graphData.edges.length > 0) {
        this.noResults = false
      }
      
      const container = this.$refs.graphContainer
      if (!container) {
        console.warn('Graph container not found')
        return
      }
      
      // Wait for next tick to ensure DOM is ready
      this.$nextTick(() => {
        this._renderGraphInternal(container)
      })
    },
    _renderGraphInternal(container) {
      // Initialize or get chart instance
      if (!this.chart) {
        this.chart = echarts.init(container)
        
        // Handle window resize
        window.addEventListener('resize', () => {
          if (this.chart) {
            this.chart.resize()
          }
        })
      }
      
      // Transform nodes for ECharts
      const nodes = this.graphData.nodes.map(node => ({
        id: node.id,
        name: node.label || node.id,
        value: node.id,
        category: node.labels && node.labels.length > 0 ? node.labels[0] : 'default',
        label: {
          show: true,
          formatter: node.label || node.id
        },
        symbolSize: 30,
        itemStyle: {
          color: this.getNodeColor(node.labels)
        },
        // Store properties for tooltip
        properties: node.properties,
        labels: node.labels || []
      }))
      
      // Transform edges for ECharts
      const edges = this.graphData.edges.map(edge => ({
        source: edge.source,
        target: edge.target,
        label: {
          show: true,
          formatter: edge.label || ''
        },
        lineStyle: {
          width: 2,
          color: '#848484',
          curveness: 0.3
        },
        // Store properties for tooltip
        properties: edge.properties || {},
        type: edge.label || ''
      }))
      
      // Get unique categories for legend
      const categories = [...new Set(nodes.map(n => n.category))]
      const categoryColors = categories.reduce((acc, cat, idx) => {
        acc[cat] = this.getCategoryColor(cat, idx)
        return acc
      }, {})
      
      // Update node colors based on category
      nodes.forEach(node => {
        node.itemStyle.color = categoryColors[node.category] || '#97C2FC'
      })
      
      const option = {
        title: {
          text: 'Graph Visualization',
          top: 'top',
          left: 'center',
          textStyle: {
            fontSize: 16
          }
        },
        tooltip: {
          trigger: 'item',
          formatter: (params) => {
            if (params.dataType === 'node') {
              const node = params.data
              const props = node.properties || {}
              const labels = node.labels || []
              
              let tooltipContent = `<div style="font-weight: bold; margin-bottom: 4px;">${node.name}</div>`
              
              if (labels.length > 0) {
                tooltipContent += `<div style="margin-bottom: 4px;"><strong>Labels:</strong> ${labels.join(', ')}</div>`
              }
              
              if (Object.keys(props).length > 0) {
                tooltipContent += `<div style="margin-top: 8px;"><strong>Properties:</strong></div>`
                tooltipContent += '<div style="margin-left: 8px; font-family: monospace; font-size: 11px;">'
                for (const [key, value] of Object.entries(props)) {
                  const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value)
                  tooltipContent += `<div>• <strong>${key}:</strong> ${valueStr}</div>`
                }
                tooltipContent += '</div>'
              }
              
              return tooltipContent
            } else if (params.dataType === 'edge') {
              const edge = params.data
              const props = edge.properties || {}
              
              let tooltipContent = `<div style="font-weight: bold; margin-bottom: 4px;">${edge.source} → ${edge.target}</div>`
              tooltipContent += `<div style="margin-bottom: 4px;"><strong>Type:</strong> ${edge.type || 'RELATED_TO'}</div>`
              
              if (Object.keys(props).length > 0) {
                tooltipContent += `<div style="margin-top: 8px;"><strong>Properties:</strong></div>`
                tooltipContent += '<div style="margin-left: 8px; font-family: monospace; font-size: 11px;">'
                for (const [key, value] of Object.entries(props)) {
                  const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value)
                  tooltipContent += `<div>• <strong>${key}:</strong> ${valueStr}</div>`
                }
                tooltipContent += '</div>'
              }
              
              return tooltipContent
            }
            return params.name
          },
          backgroundColor: 'rgba(50, 50, 50, 0.95)',
          borderColor: '#333',
          borderWidth: 1,
          textStyle: {
            color: '#fff',
            fontSize: 12
          },
          padding: [8, 12],
          extraCssText: 'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); max-width: 400px;'
        },
        legend: {
          data: categories,
          orient: 'vertical',
          left: 'left',
          top: 'middle'
        },
        series: [
          {
            name: 'Graph',
            type: 'graph',
            layout: 'force',
            data: nodes,
            links: edges,
            categories: categories.map(cat => ({ name: cat })),
            roam: true,
            label: {
              show: true,
              position: 'right',
              formatter: '{b}'
            },
            labelLayout: {
              hideOverlap: true
            },
            emphasis: {
              focus: 'adjacency',
              lineStyle: {
                width: 4
              }
            },
            force: {
              repulsion: 1000,
              gravity: 0.1,
              edgeLength: 200,
              layoutAnimation: true
            },
            lineStyle: {
              color: 'source',
              curveness: 0.3
            }
          }
        ]
      }
      
      try {
        this.chart.setOption(option, true)
      } catch (error) {
        console.error('Error setting chart option:', error)
        this.error = 'Failed to render graph visualization'
      }
    },
    getNodeColor(labels) {
      if (!labels || labels.length === 0) return '#97C2FC'
      
      // Generate color based on label
      const colors = [
        '#97C2FC', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE',
        '#85C1E2', '#F8B739', '#52BE80', '#EC7063', '#5DADE2'
      ]
      const hash = labels[0].split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
      return colors[hash % colors.length]
    },
    getCategoryColor(category, index) {
      const colors = [
        '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
        '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#97C2FC'
      ]
      return colors[index % colors.length]
    },
    onQueryInput() {
      // Don't execute queries when unlocked - user is just editing
      // Query will execute when they lock it again
    },
    updateQuery() {
      // Only execute query if locked
      if (!this.isLocked) {
        return
      }
      
      if (this.customQuery.trim()) {
        this.currentQuery = this.customQuery.trim()
        // Reset hash when query changes to force refresh
        this.lastResultHash = null
        this.fetchGraphData().then((dataUpdated) => {
          if (dataUpdated) {
            this.renderGraph()
          }
        })
      }
    },
    toggleLock() {
      this.isLocked = !this.isLocked
      if (this.isLocked) {
        // Locked: enable auto-execution and execute current query
        this.currentQuery = this.customQuery.trim()
        this.lastResultHash = null // Force refresh when locking
        this.fetchGraphData().then((dataUpdated) => {
          if (dataUpdated) {
            this.renderGraph()
          }
        })
        this.startAutoRefresh()
      } else {
        // Unlocked: disable auto-execution
        this.stopAutoRefresh()
      }
    },
    startAutoRefresh() {
      this.stopAutoRefresh() // Clear any existing interval
      this.refreshInterval = setInterval(() => {
        this.fetchGraphData().then((dataUpdated) => {
          if (dataUpdated) {
            this.renderGraph()
          }
        }).catch(error => {
          console.error('Error refreshing graph:', error)
        })
      }, 3000) // 3 seconds
    },
    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
    }
  }
}
</script>

<style scoped>
.graph-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #FFFFFF;
  border-left: 1px solid #E5E5E5;
}

.graph-header {
  padding: 20px 24px;
  border-bottom: 1px solid #E5E5E5;
  background: #FAFAFA;
}

.graph-header h3 {
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 600;
  color: #231F20;
}

.graph-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.graph-query-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
}

.graph-query-input:focus {
  outline: none;
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn-small {
  padding: 8px 16px;
  font-size: 13px;
}

.btn.active {
  background: #3B82F6;
  color: white;
}

.lock-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 100px;
  justify-content: center;
}

.lock-btn.locked {
  background: #10B981;
  color: white;
}

.lock-btn.locked:hover {
  background: #059669;
}

.lock-btn:not(.locked):hover {
  background: rgba(59, 130, 246, 0.1);
}

.lock-icon {
  font-size: 16px;
}

.lock-text {
  font-size: 13px;
  font-weight: 500;
}

.graph-query-input:disabled {
  background: #F3F4F6;
  color: #6B7280;
  cursor: not-allowed;
  opacity: 0.7;
}

.graph-visualization {
  flex: 1;
  min-height: 0;
  background: #FAFAFA;
}

.graph-error {
  padding: 16px;
  background: #FEE2E2;
  color: #991B1B;
  border-top: 1px solid #E5E5E5;
  font-size: 14px;
}

.graph-no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 24px;
  text-align: center;
  background: #FAFAFA;
  border-top: 1px solid #E5E5E5;
}

.no-results-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.no-results-message h4 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #231F20;
}

.no-results-message p {
  margin: 0;
  font-size: 14px;
  color: #6B7280;
  max-width: 500px;
}
</style>
