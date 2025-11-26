<template>
  <div class="app">
    <header class="header">
      <div class="logo-container">
        <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph Logo" class="logo" />
        <h1>GraphRAG Knowledge Graph Creation</h1>
      </div>
      <p class="subtitle">Ingest unstructured documents into Memgraph</p>
    </header>

    <div class="tabs">
      <button 
        @click="activeTab = 'ingest'" 
        :class="['tab-button', { active: activeTab === 'ingest' }]"
      >
        Document Ingestion
      </button>
      <button 
        @click="activeTab = 'retrieval'" 
        :class="['tab-button', { active: activeTab === 'retrieval' }]"
      >
        Retrieval
      </button>
      <button 
        @click="activeTab = 'stats'" 
        :class="['tab-button', { active: activeTab === 'stats' }]"
      >
        Stats
      </button>
      <button 
        @click="activeTab = 'mcp'" 
        :class="['tab-button', { active: activeTab === 'mcp' }]"
      >
        MCP
      </button>
    </div>

    <main class="main-content" v-if="activeTab === 'ingest'">
      <div class="card">
        <h2>Document Ingestion</h2>
        <form @submit.prevent="ingestDocuments" class="form">
          <div class="form-group">
            <label for="urls">Document URLs (one per line)</label>
            <textarea
              id="urls"
              v-model="urls"
              rows="6"
              placeholder="https://memgraph.com/docs/deployment/workloads&#10;https://memgraph.com/docs/deployment/workloads/memgraph-in-cybersecurity"
              class="textarea"
            ></textarea>
          </div>

          <div v-if="estimate" class="estimate-info">
            <div class="estimate-summary">
              <strong>Estimated:</strong> {{ estimate.total_chunks }} chunks • 
              {{ formatTime(estimate.total_estimated_time_seconds) }}
            </div>
            <div v-for="doc in estimate.documents" :key="doc.url" class="estimate-item">
              <span class="estimate-url">{{ doc.url }}</span>
              <span class="estimate-details">{{ doc.chunk_count }} chunks • {{ formatTime(doc.estimated_time_seconds) }}</span>
            </div>
          </div>

          <div class="form-options">
            <label class="checkbox-label">
              <input type="checkbox" v-model="onlyChunks" />
              Only create chunks (skip LightRAG processing)
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="linkChunks" />
              Link chunks with NEXT relationship
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="createVectorIndex" />
              Create vector index
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="cleanup" />
              Cleanup existing data
            </label>
          </div>

          <button type="submit" :disabled="loading || estimating" class="btn btn-primary">
            {{ loading ? 'Processing...' : estimating ? 'Estimating...' : 'Ingest Documents' }}
          </button>
        </form>
      </div>

      <div v-if="progress.length > 0" class="card progress-card" ref="progressCard">
        <h3>Progress</h3>
        
        <!-- Countdown Timer -->
        <div v-if="(countdownSeconds > 0 || countdownTimer === 0) && !ingestionFinished" class="countdown-timer" :class="{ 'countdown-finished': countdownTimer === 0 }">
          <div class="countdown-header">
            <span class="countdown-label">⏱️ Estimated Time Remaining</span>
            <span class="countdown-value" :class="{ 'countdown-warning': countdownTimer <= 10 && countdownTimer > 0 }">
              {{ countdownTimer > 0 ? countdownTimer + ' seconds' : 'Finalizing...' }}
            </span>
          </div>
          <div v-if="countdownTimer === 0" class="countdown-message">
            Ingestion will finalize shortly. Please wait...
          </div>
        </div>
        
        <div v-for="(item, index) in progress" :key="index" class="progress-item">
          <div class="progress-header">
            <span class="progress-url">{{ item.url }}</span>
            <span class="progress-status" :class="item.status">{{ item.status }}</span>
          </div>
          <div v-if="item.status === 'processing'" class="progress-bar">
            <div class="progress-bar-fill" :style="{ width: item.progress + '%' }"></div>
          </div>
          <div v-if="item.status === 'processing'" class="progress-time">
            Estimated time remaining: {{ formatTime(item.estimatedTimeRemaining) }}
          </div>
        </div>
      </div>

      <div v-if="message" class="card message" :class="messageType">
        <h3>{{ messageType === 'error' ? 'Error' : 'Success' }}</h3>
        <p>{{ message }}</p>
      </div>

      <div v-if="status" class="card status">
        <h3>Status</h3>
        <pre>{{ status }}</pre>
      </div>
    </main>

    <main class="main-content retrieval-content" v-if="activeTab === 'retrieval'">
      <div class="retrieval-layout">
        <div class="retrieval-sidebar">
          <h2>Retrieval Methods</h2>
          <div class="retrieval-tabs-vertical">
            <div class="retrieval-tab-wrapper">
              <button 
                @click="activeRetrievalMethod = 'vector-expansion'" 
                :class="['retrieval-tab-button-vertical', { active: activeRetrievalMethod === 'vector-expansion' }]"
              >
                Vector Search + Expansion
              </button>
              <div class="method-tooltip">
                <div class="method-description-tooltip">
                  <h3>Vector Search + Expansion</h3>
                  <p class="method-summary">
                    Embeds your question, finds the top-k most similar chunks via vector search, then expands through the graph using BFS and ranks results by node degree.
                  </p>
                  <div class="query-display">
                    <strong>Query:</strong>
                    <pre class="query-code">CALL embeddings.text(['{question}']) YIELD embeddings, success
CALL vector_search.search('vs_name', 5, embeddings[0]) YIELD distance, node, similarity
MATCH (node)-[r*bfs]-(dst:Chunk)
WITH DISTINCT dst, degree(dst) AS degree ORDER BY degree DESC
RETURN dst LIMIT 5</pre>
                  </div>
                </div>
              </div>
            </div>
            <div class="retrieval-tab-wrapper">
              <button 
                @click="activeRetrievalMethod = 'openai-agents'" 
                :class="['retrieval-tab-button-vertical', { active: activeRetrievalMethod === 'openai-agents' }]"
              >
                OpenAI Agents
              </button>
              <div class="method-tooltip">
                <div class="method-description-tooltip">
                  <h3>OpenAI Agents</h3>
                  <p class="method-summary">
                    Uses OpenAI Agents SDK with MCP (Model Context Protocol) to automatically select and execute tools from the MCP server. The agent intelligently chooses which tools to use based on your question.
                  </p>
                  <div class="query-display">
                    <strong>How it works:</strong>
                    <ul class="method-features" style="margin-top: 12px;">
                      <li>The agent connects to the MCP server via HTTP with SSE transport</li>
                      <li>It automatically discovers available tools from the MCP server</li>
                      <li>Based on your question, it selects and executes the appropriate tools</li>
                      <li>Returns a natural language answer based on the tool results</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="retrieval-main-content">
          <div v-if="activeRetrievalMethod === 'vector-expansion'" class="retrieval-method-content">
          <div class="card chat-card" :class="{ 'chat-fullscreen': chatFullscreen }">
            <div class="chat-header">
              <h3>Ask a Question</h3>
              <button @click="toggleChatFullscreen" class="btn-icon" :title="chatFullscreen ? 'Exit Fullscreen' : 'Fullscreen'">
                {{ chatFullscreen ? '⤓' : '⛶' }}
              </button>
            </div>
            <div class="chat-messages" ref="chatMessages">
              <div v-for="(message, index) in chatMessages" :key="index" :class="['chat-message', message.type]">
                <div v-if="message.type === 'bot'" class="message-avatar bot-avatar">
                  <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph" />
                </div>
                <div class="message-content">
                  <div class="message-header">
                    <strong>{{ message.type === 'user' ? 'You' : 'Memgraph' }}</strong>
                    <span class="message-time">{{ message.time }}</span>
                  </div>
                  <div class="message-text">{{ message.text }}</div>
                </div>
                <div v-if="message.type === 'user'" class="message-avatar user-avatar">
                  <div class="avatar-placeholder">You</div>
                </div>
              </div>
              <div v-if="chatLoading" class="chat-message bot typing-indicator">
                <div class="message-avatar bot-avatar">
                  <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph" />
                </div>
                <div class="message-content typing-content">
                  <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
            <form @submit.prevent="askQuestion" class="chat-form">
              <div class="chat-input-container">
                <textarea
                  v-model="question"
                  placeholder="Ask a question about the knowledge graph..."
                  class="chat-input"
                  rows="2"
                  :disabled="chatLoading"
                ></textarea>
                <button type="submit" :disabled="chatLoading || !question.trim()" class="btn btn-primary chat-send-btn">
                  {{ chatLoading ? 'Sending...' : 'Send' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <div v-if="activeRetrievalMethod === 'openai-agents'" class="retrieval-method-content">
          <div class="card chat-card" :class="{ 'chat-fullscreen': openaiAgentsFullscreen }">
            <div class="chat-header">
              <h3>Ask a Question</h3>
              <button @click="toggleOpenAIAgentsFullscreen" class="btn-icon" :title="openaiAgentsFullscreen ? 'Exit Fullscreen' : 'Fullscreen'">
                {{ openaiAgentsFullscreen ? '⤓' : '⛶' }}
              </button>
            </div>
            <div class="chat-messages" ref="openaiAgentsChatMessages">
              <div v-for="(message, index) in openaiAgentsMessages" :key="index" :class="['chat-message', message.type]">
                <div v-if="message.type === 'bot'" class="message-avatar bot-avatar">
                  <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph" />
                </div>
                <div class="message-content">
                  <div class="message-header">
                    <strong>{{ message.type === 'user' ? 'You' : 'Memgraph Agent' }}</strong>
                    <span class="message-time">{{ message.time }}</span>
                  </div>
                  <div class="message-text">{{ message.text }}</div>
                </div>
                <div v-if="message.type === 'user'" class="message-avatar user-avatar">
                  <div class="avatar-placeholder">You</div>
                </div>
              </div>
              <div v-if="openaiAgentsLoading" class="chat-message bot typing-indicator">
                <div class="message-avatar bot-avatar">
                  <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph" />
                </div>
                <div class="message-content typing-content">
                  <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
            <form @submit.prevent="askOpenAIAgent" class="chat-form">
              <div class="chat-input-container">
                <textarea
                  v-model="openaiAgentsQuestion"
                  placeholder="Ask a question about the knowledge graph..."
                  class="chat-input"
                  rows="2"
                  :disabled="openaiAgentsLoading"
                ></textarea>
                <button type="submit" :disabled="openaiAgentsLoading || !openaiAgentsQuestion.trim()" class="btn btn-primary chat-send-btn">
                  {{ openaiAgentsLoading ? 'Sending...' : 'Send' }}
                </button>
              </div>
            </form>
          </div>
        </div>
        </div>
      </div>
    </main>

    <main class="main-content" v-if="activeTab === 'stats'">
      <div class="card">
        <div class="stats-header">
          <h2>Knowledge Graph Statistics</h2>
          <div class="header-buttons">
            <button @click="fetchStats" :disabled="statsLoading" class="btn btn-primary refresh-btn">
              {{ statsLoading ? 'Loading...' : 'Refresh' }}
            </button>
          </div>
        </div>

        <div v-if="statsError" class="message error">
          <p>{{ statsError }}</p>
        </div>

        <div v-if="stats && !statsLoading" class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">📄</div>
            <div class="stat-content">
              <div class="stat-label">Chunks</div>
              <div class="stat-value">{{ formatNumber(stats.chunks) }}</div>
              <div class="stat-description">Document chunks in the graph</div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon">🔗</div>
            <div class="stat-content">
              <div class="stat-label">Entities</div>
              <div class="stat-value">{{ formatNumber(stats.entities) }}</div>
              <div class="stat-description">Knowledge graph entities</div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon">🔀</div>
            <div class="stat-content">
              <div class="stat-label">Relationships</div>
              <div class="stat-value">{{ formatNumber(stats.relationships) }}</div>
              <div class="stat-description">Connections between nodes</div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-content">
              <div class="stat-label">Total Nodes</div>
              <div class="stat-value">{{ formatNumber(stats.nodes) }}</div>
              <div class="stat-description">All nodes in the knowledge graph</div>
            </div>
          </div>
        </div>

        <div v-if="!stats && !statsLoading && !statsError" class="stats-empty">
          <p>Click "Refresh" to load statistics from the knowledge graph.</p>
        </div>
      </div>
    </main>

    <main class="main-content" v-if="activeTab === 'mcp'">
      <div class="card">
        <div class="stats-header">
          <h2>MCP Server</h2>
          <div class="header-buttons">
            <button @click="testMCPConnection" :disabled="mcpTesting" class="btn btn-secondary">
              {{ mcpTesting ? 'Testing...' : 'Test Connection' }}
            </button>
            <button @click="listMCPTools" :disabled="toolsLoading" class="btn btn-primary">
              {{ toolsLoading ? 'Loading...' : 'List Tools' }}
            </button>
          </div>
        </div>
        
        <div v-if="mcpTestResult" class="mcp-test-result" :class="mcpTestResult.status">
          <div class="mcp-test-header">
            <strong>MCP Connection Test</strong>
            <span class="mcp-test-status">{{ mcpTestResult.status === 'success' ? '✓ Connected' : '✗ Failed' }}</span>
          </div>
          <div v-if="mcpTestResult.status === 'success'" class="mcp-test-details">
            <p><strong>URL:</strong> {{ mcpTestResult.mcp_url }}</p>
            <p><strong>Status:</strong> {{ mcpTestResult.status }}</p>
            
            <!-- Schema Display -->
            <div v-if="mcpTestResult.schema" class="schema-display">
              <h4>📋 Graph Schema</h4>
              <div v-if="mcpTestResult.schema.nodeLabels && mcpTestResult.schema.nodeLabels.length > 0" class="schema-section">
                <h5>Node Labels ({{ mcpTestResult.schema.nodeLabels.length }})</h5>
                <div class="schema-tags">
                  <span v-for="label in mcpTestResult.schema.nodeLabels" :key="label" class="schema-tag node-tag">
                    {{ label }}
                  </span>
                </div>
              </div>
              
              <div v-if="mcpTestResult.schema.relationshipTypes && mcpTestResult.schema.relationshipTypes.length > 0" class="schema-section">
                <h5>Relationship Types ({{ mcpTestResult.schema.relationshipTypes.length }})</h5>
                <div class="schema-tags">
                  <span v-for="relType in mcpTestResult.schema.relationshipTypes" :key="relType" class="schema-tag rel-tag">
                    {{ relType }}
                  </span>
                </div>
              </div>
              
              <div v-if="mcpTestResult.schema.properties && Object.keys(mcpTestResult.schema.properties).length > 0" class="schema-section">
                <h5>Properties</h5>
                <div class="properties-list">
                  <div v-for="(props, label) in mcpTestResult.schema.properties" :key="label" class="property-group">
                    <strong class="property-label">{{ label }}:</strong>
                    <span v-for="prop in props" :key="prop" class="schema-tag prop-tag">
                      {{ prop }}
                    </span>
                  </div>
                </div>
              </div>
              
              <details v-if="mcpTestResult.mcp_response" class="mcp-response-details">
                <summary>Raw MCP Response</summary>
                <pre>{{ JSON.stringify(mcpTestResult.mcp_response, null, 2) }}</pre>
              </details>
            </div>
            
            <div v-else-if="mcpTestResult.mcp_response" class="mcp-response-fallback">
              <details class="mcp-response-details">
                <summary>MCP Response</summary>
                <pre>{{ JSON.stringify(mcpTestResult.mcp_response, null, 2) }}</pre>
              </details>
            </div>
          </div>
          <div v-else class="mcp-test-error">
            <p><strong>Error:</strong> {{ mcpTestResult.error }}</p>
          </div>
        </div>

        <div v-if="toolsError" class="message error">
          <p>{{ toolsError }}</p>
        </div>

        <div v-if="mcpTools && mcpTools.length > 0" class="tools-section">
          <h3>Available MCP Tools ({{ mcpTools.length }})</h3>
          <div class="tools-grid">
            <div v-for="tool in mcpTools" :key="tool.name" class="tool-card">
              <div class="tool-header">
                <h4 class="tool-name">{{ tool.name }}</h4>
              </div>
              <div v-if="tool.description" class="tool-description">
                {{ tool.description }}
              </div>
              <div v-if="tool.inputSchema && tool.inputSchema.properties" class="tool-parameters">
                <strong>Parameters:</strong>
                <ul class="tool-params-list">
                  <li v-for="(param, paramName) in tool.inputSchema.properties" :key="paramName">
                    <code>{{ paramName }}</code>
                    <span v-if="param.type">: {{ param.type }}</span>
                    <span v-if="param.description"> - {{ param.description }}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!mcpTools && !toolsLoading && !toolsError" class="tools-empty">
          <p>Click "List Tools" to see available MCP server tools.</p>
        </div>

        <div class="call-tool-section">
          <h3>Call MCP Tool</h3>
          <form @submit.prevent="callTool" class="call-tool-form">
            <div class="form-group">
              <label for="selectedTool">Select Tool</label>
              <select 
                id="selectedTool"
                v-model="selectedToolName"
                @change="onToolSelected"
                class="select-input"
                :disabled="!mcpTools || mcpTools.length === 0 || toolCalling"
              >
                <option value="">-- Select a tool --</option>
                <option v-for="tool in mcpTools" :key="tool.name" :value="tool.name">
                  {{ tool.name }}
                </option>
              </select>
            </div>

            <div v-if="selectedTool && selectedTool.inputSchema && selectedTool.inputSchema.properties" class="tool-arguments">
              <h4>Arguments</h4>
              <div v-for="(param, paramName) in selectedTool.inputSchema.properties" :key="paramName" class="form-group">
                <label :for="`arg-${paramName}`">
                  {{ paramName }}
                  <span v-if="param.type" class="param-type">({{ param.type }})</span>
                  <span v-if="isRequired(paramName)" class="required">*</span>
                </label>
                <div v-if="param.description" class="param-description">{{ param.description }}</div>
                <input
                  v-if="param.type === 'string' || param.type === 'integer' || param.type === 'number'"
                  :id="`arg-${paramName}`"
                  v-model="toolArguments[paramName]"
                  :type="param.type === 'integer' || param.type === 'number' ? 'number' : 'text'"
                  :placeholder="param.default !== undefined ? `Default: ${param.default}` : ''"
                  class="input-field"
                  :disabled="toolCalling"
                />
                <textarea
                  v-else-if="param.type === 'array' || param.type === 'object'"
                  :id="`arg-${paramName}`"
                  v-model="toolArguments[paramName]"
                  :placeholder="param.default !== undefined ? `Default: ${JSON.stringify(param.default)}` : 'Enter JSON'"
                  rows="4"
                  class="textarea"
                  :disabled="toolCalling"
                ></textarea>
                <input
                  v-else
                  :id="`arg-${paramName}`"
                  v-model="toolArguments[paramName]"
                  type="text"
                  :placeholder="param.default !== undefined ? `Default: ${param.default}` : ''"
                  class="input-field"
                  :disabled="toolCalling"
                />
              </div>
            </div>

            <div v-if="selectedTool && (!selectedTool.inputSchema || !selectedTool.inputSchema.properties || Object.keys(selectedTool.inputSchema.properties).length === 0)" class="no-arguments">
              <p>This tool does not require any arguments.</p>
            </div>

            <button type="submit" :disabled="!selectedToolName || toolCalling" class="btn btn-primary">
              {{ toolCalling ? 'Calling...' : 'Call Tool' }}
            </button>
          </form>

          <div v-if="toolCallError" class="message error">
            <p><strong>Error:</strong> {{ toolCallError }}</p>
          </div>

          <div v-if="toolCallResult" class="tool-result">
            <h4>Result</h4>
            <div class="result-info">
              <p><strong>Tool:</strong> {{ toolCallResult.tool_name }}</p>
              <p v-if="toolCallResult.arguments && Object.keys(toolCallResult.arguments).length > 0">
                <strong>Arguments:</strong> {{ JSON.stringify(toolCallResult.arguments, null, 2) }}
              </p>
            </div>
            <div class="result-content">
              <pre>{{ formatToolResult(toolCallResult.result) }}</pre>
            </div>
            <details v-if="toolCallResult.mcp_response" class="mcp-response-details">
              <summary>Raw MCP Response</summary>
              <pre>{{ JSON.stringify(toolCallResult.mcp_response, null, 2) }}</pre>
            </details>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      activeTab: 'ingest',
      activeRetrievalMethod: 'vector-expansion',
      urls: '',
      onlyChunks: false,
      linkChunks: true,
      createVectorIndex: true,
      cleanup: true,
      loading: false,
      estimating: false,
      message: '',
      messageType: '',
      status: '',
      estimate: null,
      progress: [],
      question: '',
      chatLoading: false,
      chatMessages: [],
      openaiAgentsQuestion: '',
      openaiAgentsLoading: false,
      openaiAgentsMessages: [],
      chatFullscreen: false,
      openaiAgentsFullscreen: false,
      stats: null,
      statsLoading: false,
      statsError: '',
      mcpTesting: false,
      mcpTestResult: null,
      mcpTools: null,
      toolsLoading: false,
      toolsError: '',
      selectedToolName: '',
      toolArguments: {},
      toolCalling: false,
      toolCallResult: null,
      toolCallError: '',
      countdownTimer: null,
      countdownSeconds: 0,
      countdownInterval: null,
      ingestionFinished: false
    }
  },
  mounted() {
    // Auto-fetch stats when stats tab is first accessed
    this.$watch('activeTab', (newTab) => {
      if (newTab === 'stats' && !this.stats && !this.statsLoading) {
        this.fetchStats()
      }
    })
  },
  beforeUnmount() {
    // Clean up countdown interval when component is destroyed
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval)
    }
    // Restore body overflow if in fullscreen
    if (this.chatFullscreen || this.openaiAgentsFullscreen) {
      document.body.style.overflow = ''
    }
  },
  watch: {
    urls: {
      handler: 'estimateChunks',
      immediate: false
    },
    progress: {
      handler() {
        this.$nextTick(() => {
          this.scrollToProgress()
        })
      },
      deep: true
    },
    chatLoading(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          this.scrollChatToBottom()
        })
      }
    },
    openaiAgentsLoading(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          this.scrollOpenAIAgentsChatToBottom()
        })
      }
    }
  },
  methods: {
    scrollToProgress() {
      // Scroll to the very bottom of the page
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: 'smooth'
      })
    },
    formatTime(seconds) {
      if (seconds >= 3600) {
        return `${(seconds / 3600).toFixed(1)} hours`
      } else if (seconds >= 60) {
        return `${(seconds / 60).toFixed(1)} minutes`
      } else {
        return `${seconds.toFixed(0)} seconds`
      }
    },
    async estimateChunks() {
      const urlList = this.urls
        .split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0)

      if (urlList.length === 0) {
        this.estimate = null
        return
      }

      this.estimating = true
      try {
        const response = await axios.post('/api/ingest/estimate', {
          urls: urlList
        })
        this.estimate = response.data
      } catch (error) {
        // Silently fail estimation
        this.estimate = null
      } finally {
        this.estimating = false
      }
    },
    async ingestDocuments() {
      this.loading = true
      this.message = ''
      this.status = ''
      this.messageType = ''
      this.progress = []
      
      // Clear any existing countdown timer
      if (this.countdownInterval) {
        clearInterval(this.countdownInterval)
        this.countdownInterval = null
      }
      this.ingestionFinished = false

      const urlList = this.urls
        .split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0)

      if (urlList.length === 0) {
        this.message = 'Please provide at least one URL'
        this.messageType = 'error'
        this.loading = false
        return
      }

      // Calculate total estimated time and start countdown
      let totalEstimatedSeconds = 0
      if (this.estimate && this.estimate.total_estimated_time_seconds) {
        totalEstimatedSeconds = Math.ceil(this.estimate.total_estimated_time_seconds)
      } else {
        // Fallback: calculate from chunk count (10 seconds per chunk)
        const estimateMap = {}
        if (this.estimate) {
          this.estimate.documents.forEach(doc => {
            estimateMap[doc.url] = doc.chunk_count
            totalEstimatedSeconds += doc.chunk_count * 10
          })
        }
      }
      
      // Start countdown timer
      if (totalEstimatedSeconds > 0) {
        this.countdownTimer = totalEstimatedSeconds
        this.countdownSeconds = totalEstimatedSeconds
        this.startCountdown()
      }

      // Initialize progress tracking
      const estimateMap = {}
      if (this.estimate) {
        this.estimate.documents.forEach(doc => {
          estimateMap[doc.url] = doc.chunk_count
        })
      }

      // Process documents one by one
      let firstDocument = true
      for (const url of urlList) {
        const chunkCount = estimateMap[url] || 0
        const estimatedTime = chunkCount * 10 // 10 seconds per chunk
        
        this.progress.push({
          url: url,
          status: 'processing',
          progress: 0,
          estimatedTimeRemaining: estimatedTime,
          totalChunks: chunkCount,
          processedChunks: 0
        })
        
        // Scroll to progress section
        this.$nextTick(() => {
          this.scrollToProgress()
        })

        try {
          const response = await axios.post('/api/ingest/single', {
            url: url,
            only_chunks: this.onlyChunks,
            link_chunks: this.linkChunks,
            create_vector_index: this.createVectorIndex,
            cleanup: firstDocument && this.cleanup
          })

          const progressItem = this.progress.find(p => p.url === url)
          if (progressItem) {
            progressItem.status = 'completed'
            progressItem.progress = 100
          }
          
          // Scroll to show completed status
          this.$nextTick(() => {
            this.scrollToProgress()
          })
        } catch (error) {
          const progressItem = this.progress.find(p => p.url === url)
          if (progressItem) {
            progressItem.status = 'error'
          }
          this.message = error.response?.data?.detail || error.message || 'An error occurred'
          this.messageType = 'error'
          if (error.response?.data) {
            this.status = JSON.stringify(error.response.data, null, 2)
          }
          
          // Stop countdown timer on error
          if (this.countdownInterval) {
            clearInterval(this.countdownInterval)
            this.countdownInterval = null
          }
          this.countdownTimer = null
          this.ingestionFinished = false
          
          // Scroll to show error
          this.$nextTick(() => {
            this.scrollToProgress()
          })
          break
        }

        firstDocument = false
      }

      if (this.progress.every(p => p.status === 'completed')) {
        this.message = `Successfully ingested ${urlList.length} document(s)!`
        this.messageType = 'success'
        // Stop countdown timer and mark as finished
        if (this.countdownInterval) {
          clearInterval(this.countdownInterval)
          this.countdownInterval = null
        }
        this.ingestionFinished = true
      }

      this.loading = false
    },
    startCountdown() {
      // Clear any existing interval
      if (this.countdownInterval) {
        clearInterval(this.countdownInterval)
      }
      
      // Update countdown every second
      this.countdownInterval = setInterval(() => {
        if (this.countdownTimer > 0) {
          this.countdownTimer--
        } else {
          // Timer reached 0, keep it at 0 to show "Finalizing..." message
          this.countdownTimer = 0
        }
      }, 1000)
    },
    async askQuestion() {
      if (!this.question.trim() || this.chatLoading) {
        return
      }

      const userQuestion = this.question.trim()
      this.question = ''
      this.chatLoading = true

      // Add user message
      const userMessage = {
        type: 'user',
        text: userQuestion,
        time: new Date().toLocaleTimeString()
      }
      this.chatMessages.push(userMessage)

      // Scroll to bottom to show typing indicator
      this.$nextTick(() => {
        this.scrollChatToBottom()
      })

      try {
        const response = await axios.post('/api/query', {
          question: userQuestion
        })

        // Add bot response
        const botMessage = {
          type: 'bot',
          text: response.data.answer || 'No answer provided.',
          time: new Date().toLocaleTimeString()
        }
        this.chatMessages.push(botMessage)
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.chatMessages.push(errorMessage)
      } finally {
        this.chatLoading = false
        this.$nextTick(() => {
          this.scrollChatToBottom()
        })
      }
    },
    scrollChatToBottom() {
      if (this.$refs.chatMessages) {
        this.$refs.chatMessages.scrollTop = this.$refs.chatMessages.scrollHeight
      }
    },
    scrollOpenAIAgentsChatToBottom() {
      if (this.$refs.openaiAgentsChatMessages) {
        this.$refs.openaiAgentsChatMessages.scrollTop = this.$refs.openaiAgentsChatMessages.scrollHeight
      }
    },
    toggleChatFullscreen() {
      this.chatFullscreen = !this.chatFullscreen
      if (this.chatFullscreen) {
        document.body.style.overflow = 'hidden'
      } else {
        document.body.style.overflow = ''
      }
    },
    toggleOpenAIAgentsFullscreen() {
      this.openaiAgentsFullscreen = !this.openaiAgentsFullscreen
      if (this.openaiAgentsFullscreen) {
        document.body.style.overflow = 'hidden'
      } else {
        document.body.style.overflow = ''
      }
    },
    async askOpenAIAgent() {
      if (!this.openaiAgentsQuestion.trim() || this.openaiAgentsLoading) {
        return
      }

      const userQuestion = this.openaiAgentsQuestion.trim()
      this.openaiAgentsQuestion = ''
      this.openaiAgentsLoading = true

      // Add user message
      const userMessage = {
        type: 'user',
        text: userQuestion,
        time: new Date().toLocaleTimeString()
      }
      this.openaiAgentsMessages.push(userMessage)

      // Scroll to bottom to show typing indicator
      this.$nextTick(() => {
        this.scrollOpenAIAgentsChatToBottom()
      })
      
      // Keep scrolling while loading to follow typing indicator
      const scrollInterval = setInterval(() => {
        if (this.openaiAgentsLoading) {
          this.scrollOpenAIAgentsChatToBottom()
        } else {
          clearInterval(scrollInterval)
        }
      }, 100)

      try {
        const response = await axios.post('/api/openai-agents/query', {
          question: userQuestion
        })

        // Add agent response
        const agentMessage = {
          type: 'bot',
          text: response.data.answer || 'No answer provided.',
          time: new Date().toLocaleTimeString()
        }
        this.openaiAgentsMessages.push(agentMessage)
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.openaiAgentsMessages.push(errorMessage)
      } finally {
        this.openaiAgentsLoading = false
        this.$nextTick(() => {
          this.scrollOpenAIAgentsChatToBottom()
        })
      }
    },
    async fetchStats() {
      this.statsLoading = true
      this.statsError = ''
      try {
        const response = await axios.get('/api/stats')
        this.stats = response.data
      } catch (error) {
        this.statsError = error.response?.data?.detail || error.message || 'Failed to fetch statistics'
        this.stats = null
      } finally {
        this.statsLoading = false
      }
    },
    formatNumber(num) {
      if (num === null || num === undefined) return '0'
      return num.toLocaleString()
    },
    async testMCPConnection() {
      this.mcpTesting = true
      this.mcpTestResult = null
      try {
        const response = await axios.get('/api/mcp/test')
        const mcpResponse = response.data.mcp_response
        
        // Extract schema from MCP response
        let schema = null
        if (mcpResponse && mcpResponse.result && mcpResponse.result.content) {
          const content = mcpResponse.result.content
          // Content is typically an array of objects from get_schema tool
          if (Array.isArray(content) && content.length > 0) {
            // Parse schema information from the content
            schema = this.parseSchemaFromContent(content)
          }
        }
        
        this.mcpTestResult = {
          status: 'success',
          mcp_url: response.data.mcp_url,
          mcp_response: mcpResponse,
          schema: schema
        }
      } catch (error) {
        this.mcpTestResult = {
          status: 'error',
          error: error.response?.data?.detail || error.message || 'Failed to connect to MCP service'
        }
      } finally {
        this.mcpTesting = false
      }
    },
    parseSchemaFromContent(content) {
      // Parse the schema content returned by get_schema tool
      // Format from SHOW SCHEMA INFO: [("node"/"relationship", "LabelName"/"RelType", {properties}), ...]
      const schema = {
        nodeLabels: [],
        relationshipTypes: [],
        properties: {}
      }
      
      if (!Array.isArray(content)) {
        return schema
      }
      
      content.forEach(item => {
        // Handle tuple format: ["node", "LabelName", {"prop": "type", ...}]
        if (Array.isArray(item) && item.length >= 2) {
          const elementType = item[0] // "node" or "relationship"
          const elementName = item[1] // label or relationship type
          const properties = item[2] || {} // properties dict
          
          if (elementType === 'node') {
            if (!schema.nodeLabels.includes(elementName)) {
              schema.nodeLabels.push(elementName)
            }
            if (properties && typeof properties === 'object') {
              if (!schema.properties[elementName]) {
                schema.properties[elementName] = []
              }
              const propKeys = Object.keys(properties)
              propKeys.forEach(prop => {
                if (!schema.properties[elementName].includes(prop)) {
                  schema.properties[elementName].push(prop)
                }
              })
            }
          } else if (elementType === 'relationship') {
            if (!schema.relationshipTypes.includes(elementName)) {
              schema.relationshipTypes.push(elementName)
            }
          }
        }
        // Handle object format: {element_type: "node", element_name: "Label", properties: {...}}
        else if (typeof item === 'object' && item !== null) {
          const elementType = item.element_type || item.type
          const elementName = item.element_name || item.name || item.label
          const properties = item.properties || {}
          
          if (elementType === 'node' || item.node_labels) {
            const labels = item.node_labels || (elementName ? [elementName] : [])
            labels.forEach(label => {
              if (!schema.nodeLabels.includes(label)) {
                schema.nodeLabels.push(label)
              }
              if (properties && typeof properties === 'object') {
                if (!schema.properties[label]) {
                  schema.properties[label] = []
                }
                const propKeys = Array.isArray(properties) ? properties : Object.keys(properties)
                propKeys.forEach(prop => {
                  const propName = typeof prop === 'string' ? prop : (prop.key || prop.name || prop)
                  if (propName && !schema.properties[label].includes(propName)) {
                    schema.properties[label].push(propName)
                  }
                })
              }
            })
          }
          
          if (elementType === 'relationship' || item.relationship_types) {
            const relTypes = item.relationship_types || (elementName ? [elementName] : [])
            relTypes.forEach(relType => {
              if (!schema.relationshipTypes.includes(relType)) {
                schema.relationshipTypes.push(relType)
              }
            })
          }
        }
      })
      
      // Sort for better display
      schema.nodeLabels.sort()
      schema.relationshipTypes.sort()
      Object.keys(schema.properties).forEach(label => {
        schema.properties[label].sort()
      })
      
      return schema
    },
    async listMCPTools() {
      this.toolsLoading = true
      this.toolsError = ''
      this.mcpTools = null
      try {
        const response = await axios.get('/api/mcp/tools')
        this.mcpTools = response.data.tools || []
      } catch (error) {
        this.toolsError = error.response?.data?.detail || error.message || 'Failed to list MCP tools'
        this.mcpTools = null
      } finally {
        this.toolsLoading = false
      }
    },
    onToolSelected() {
      // Reset arguments when tool changes
      this.toolArguments = {}
      this.toolCallResult = null
      this.toolCallError = ''
      
      // Initialize arguments with default values if available
      if (this.selectedTool && this.selectedTool.inputSchema && this.selectedTool.inputSchema.properties) {
        const props = this.selectedTool.inputSchema.properties
        Object.keys(props).forEach(paramName => {
          const param = props[paramName]
          if (param.default !== undefined) {
            this.toolArguments[paramName] = param.default
          }
        })
      }
    },
    isRequired(paramName) {
      if (!this.selectedTool || !this.selectedTool.inputSchema || !this.selectedTool.inputSchema.required) {
        return false
      }
      return this.selectedTool.inputSchema.required.includes(paramName)
    },
    async callTool() {
      if (!this.selectedToolName) {
        return
      }

      this.toolCalling = true
      this.toolCallError = ''
      this.toolCallResult = null

      try {
        // Parse arguments - handle JSON strings for complex types
        const parsedArguments = {}
        if (this.selectedTool && this.selectedTool.inputSchema && this.selectedTool.inputSchema.properties) {
          Object.keys(this.toolArguments).forEach(paramName => {
            const value = this.toolArguments[paramName]
            const param = this.selectedTool.inputSchema.properties[paramName]
            
            if (value === '' || value === null || value === undefined) {
              // Skip empty values unless required
              if (!this.isRequired(paramName)) {
                return
              }
            }
            
            // Try to parse JSON for array/object types
            if (param.type === 'array' || param.type === 'object') {
              try {
                parsedArguments[paramName] = JSON.parse(value)
              } catch (e) {
                // If parsing fails, use as string
                parsedArguments[paramName] = value
              }
            } else if (param.type === 'integer' || param.type === 'number') {
              parsedArguments[paramName] = Number(value)
            } else {
              parsedArguments[paramName] = value
            }
          })
        }

        const response = await axios.post('/api/mcp/call', {
          tool_name: this.selectedToolName,
          arguments: parsedArguments
        })

        this.toolCallResult = response.data
      } catch (error) {
        this.toolCallError = error.response?.data?.detail || error.message || 'Failed to call tool'
        this.toolCallResult = null
      } finally {
        this.toolCalling = false
      }
    },
    formatToolResult(result) {
      if (result === null || result === undefined) {
        return 'No result returned'
      }
      if (typeof result === 'string') {
        return result
      }
      if (Array.isArray(result)) {
        return JSON.stringify(result, null, 2)
      }
      if (typeof result === 'object') {
        return JSON.stringify(result, null, 2)
      }
      return String(result)
    }
  },
  computed: {
    selectedTool() {
      if (!this.mcpTools || !this.selectedToolName) {
        return null
      }
      return this.mcpTools.find(tool => tool.name === this.selectedToolName) || null
    }
  }
}
</script>

<style scoped>
.app {
  padding: 20px;
}

.header {
  text-align: center;
  color: #1a1a2e;
  margin-bottom: 40px;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}

.logo {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  object-fit: contain;
  background: rgba(255, 255, 255, 0.9);
  padding: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.header h1 {
  font-size: 2.5rem;
  margin: 0;
  font-weight: 600;
  color: #1a1a2e;
}

.subtitle {
  font-size: 1.2rem;
  opacity: 0.8;
  color: #495057;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.card h2 {
  margin-bottom: 20px;
  color: #1a1a2e;
}

.card h3 {
  margin-bottom: 10px;
  color: #1a1a2e;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: #495057;
}

.textarea {
  width: 100%;
  padding: 12px;
  background: #ffffff;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.3s;
  color: #212529;
}

.textarea:focus {
  outline: none;
  border-color: #4a90e2;
}

.estimate-info {
  background: #f8f9fa;
  border: 1px solid #4a90e2;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.estimate-summary {
  font-size: 14px;
  color: #1a1a2e;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #dee2e6;
}

.estimate-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 13px;
}

.estimate-url {
  color: #495057;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
}

.estimate-details {
  color: #1a1a2e;
  font-weight: 500;
  white-space: nowrap;
}

.progress-card {
  margin-top: 20px;
}

.progress-item {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e9ecef;
}

.progress-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-url {
  color: #1a1a2e;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
}

.progress-status {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
  text-transform: uppercase;
}

.progress-status.processing {
  background: #e3f2fd;
  color: #1976d2;
  border: 1px solid #90caf9;
}

.progress-status.completed {
  background: #e8f5e9;
  color: #388e3c;
  border: 1px solid #a5d6a7;
}

.progress-status.error {
  background: #ffebee;
  color: #d32f2f;
  border: 1px solid #ef9a9a;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4a90e2 0%, #357abd 100%);
  transition: width 0.3s ease;
}

.progress-time {
  font-size: 12px;
  color: #6c757d;
}

.form-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message {
  border-left: 4px solid;
}

.message h3 {
  color: #1a1a2e;
}

.message p {
  color: #495057;
}

.message.success {
  border-color: #4a90e2;
  background: #f0f4f8;
}

.message.error {
  border-color: #ef4444;
  background: #fff5f5;
}

.status {
  background: #f8f9fa;
}

.status pre {
  background: #1a1a2e;
  color: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 14px;
  line-height: 1.5;
  border: 1px solid #e9ecef;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e9ecef;
}

.tab-button {
  padding: 12px 24px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  font-size: 16px;
  font-weight: 600;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: -2px;
}

.tab-button:hover {
  color: #1a1a2e;
  background: #f8f9fa;
}

.tab-button.active {
  color: #4a90e2;
  border-bottom-color: #4a90e2;
}

.retrieval-content {
  width: 100%;
}

.retrieval-layout {
  display: flex;
  gap: 24px;
  height: calc(100vh - 200px);
  min-height: 600px;
}

.retrieval-sidebar {
  width: 250px;
  flex-shrink: 0;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
}

.retrieval-sidebar h2 {
  margin: 0 0 24px 0;
  color: #1a1a2e;
  font-size: 20px;
  font-weight: 600;
}

.retrieval-main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.retrieval-tabs-vertical {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.retrieval-tab-wrapper {
  position: relative;
}

.retrieval-tab-button-vertical {
  padding: 14px 18px;
  background: transparent;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.3s;
  text-align: left;
  width: 100%;
}

.retrieval-tab-button-vertical:hover {
  color: #1a1a2e;
  background: #f8f9fa;
  border-color: #dee2e6;
}

.retrieval-tab-button-vertical.active {
  color: #4a90e2;
  background: #f0f4f8;
  border-color: #4a90e2;
  box-shadow: 0 2px 4px rgba(74, 144, 226, 0.1);
}

.method-tooltip {
  position: absolute;
  left: calc(100% + 16px);
  top: 0;
  width: 400px;
  max-height: 80vh;
  overflow-y: auto;
  background: white;
  border: 2px solid #4a90e2;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transform: translateX(-10px);
  transition: all 0.3s ease;
  pointer-events: none;
}

.retrieval-tab-wrapper:hover .method-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateX(0);
  pointer-events: auto;
}

.method-description-tooltip {
  padding: 20px;
}

.method-description-tooltip h3 {
  margin: 0 0 12px 0;
  color: #1a1a2e;
  font-size: 18px;
  font-weight: 600;
}

.method-description-tooltip .method-summary {
  margin: 0 0 16px 0;
  color: #495057;
  font-size: 14px;
  line-height: 1.6;
}

.method-description-tooltip .query-display {
  margin-top: 16px;
}

.method-description-tooltip .query-display strong {
  display: block;
  margin-bottom: 8px;
  color: #1a1a2e;
  font-size: 14px;
}

.method-description-tooltip .query-code {
  background: #1a1a2e;
  color: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  margin: 0;
  border: 1px solid #e9ecef;
}

.method-description-tooltip .method-features {
  margin: 0;
  padding-left: 20px;
  color: #495057;
  font-size: 14px;
  line-height: 1.8;
}

.method-description-tooltip .method-features li {
  margin-bottom: 8px;
}

.chat-content {
  max-width: 900px;
  margin: 0 auto;
}

.chat-card {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 250px);
  min-height: 600px;
  position: relative;
  transition: all 0.3s ease;
}

.chat-card.chat-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  height: 100vh;
  z-index: 9999;
  border-radius: 0;
  margin: 0;
  padding: 20px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e9ecef;
}

.chat-header h3 {
  margin: 0;
  color: #1a1a2e;
  font-size: 20px;
}

.btn-icon {
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.3s;
  color: #495057;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 40px;
}

.btn-icon:hover {
  background: #e9ecef;
  border-color: #4a90e2;
  color: #4a90e2;
  transform: scale(1.05);
}

.chat-card h2 {
  margin-bottom: 20px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: linear-gradient(to bottom, #ffffff 0%, #f8f9fa 100%);
  border-radius: 12px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid #e9ecef;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
}

.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.chat-message {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-message.user {
  justify-content: flex-end;
}

.chat-message.bot {
  justify-content: flex-start;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
  border: 2px solid #e9ecef;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.bot-avatar {
  order: 0;
}

.user-avatar {
  order: 2;
}

.message-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.typing-indicator {
  opacity: 0.8;
}

.typing-content {
  padding: 16px 20px;
  background: white;
  border-bottom-left-radius: 4px;
  border-left: 3px solid #4a90e2;
}

.typing-dots {
  display: flex;
  gap: 6px;
  align-items: center;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4a90e2;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.message-content {
  max-width: 75%;
  padding: 14px 18px;
  border-radius: 16px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease;
}

.message-content:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.chat-message.user .message-content {
  background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.chat-message.bot .message-content {
  background: white;
  color: #1a1a2e;
  border-bottom-left-radius: 4px;
  border-left: 3px solid #4a90e2;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 12px;
  opacity: 0.8;
}

.message-text {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.chat-form {
  margin-top: auto;
}

.chat-input-container {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 14px 16px;
  border: 2px solid #dee2e6;
  border-radius: 12px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  transition: all 0.3s;
  color: #212529;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.chat-input:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
}

.chat-input:focus {
  outline: none;
  border-color: #4a90e2;
}

.chat-input:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
}

.chat-send-btn {
  padding: 12px 32px;
  white-space: nowrap;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.stats-header h2 {
  margin: 0;
}

.refresh-btn {
  padding: 10px 20px;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-top: 20px;
}

.stat-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #4a90e2;
}

.stat-icon {
  font-size: 32px;
  line-height: 1;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  font-weight: 600;
  color: #6c757d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 8px;
  line-height: 1.2;
}

.stat-description {
  font-size: 13px;
  color: #6c757d;
  line-height: 1.4;
}

.stats-empty {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
  font-size: 16px;
}

.header-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-secondary {
  background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(108, 117, 125, 0.4);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.mcp-test-result {
  margin-bottom: 30px;
  padding: 20px;
  border-radius: 8px;
  border: 2px solid;
}

.mcp-test-result.success {
  background: #f0f4f8;
  border-color: #4a90e2;
}

.mcp-test-result.error {
  background: #fff5f5;
  border-color: #ef4444;
}

.mcp-test-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 16px;
}

.mcp-test-status {
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
}

.mcp-test-result.success .mcp-test-status {
  background: #e8f5e9;
  color: #388e3c;
}

.mcp-test-result.error .mcp-test-status {
  background: #ffebee;
  color: #d32f2f;
}

.mcp-test-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  color: #495057;
}

.mcp-test-details p {
  margin: 0;
}

.mcp-test-error {
  color: #d32f2f;
  font-size: 14px;
}

.mcp-test-error p {
  margin: 0;
}

.mcp-response-details {
  margin-top: 12px;
}

.mcp-response-details summary {
  cursor: pointer;
  font-weight: 600;
  color: #4a90e2;
  margin-bottom: 8px;
}

.mcp-response-details summary:hover {
  text-decoration: underline;
}

.mcp-response-details pre {
  background: #1a1a2e;
  color: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.5;
  border: 1px solid #e9ecef;
  margin-top: 8px;
}

.schema-display {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.schema-display h4 {
  margin: 0 0 16px 0;
  color: #1a1a2e;
  font-size: 18px;
}

.schema-section {
  margin-bottom: 20px;
}

.schema-section h5 {
  margin: 0 0 12px 0;
  color: #495057;
  font-size: 14px;
  font-weight: 600;
}

.schema-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.schema-tag {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid;
}

.node-tag {
  background: #e3f2fd;
  color: #1976d2;
  border-color: #90caf9;
}

.rel-tag {
  background: #f3e5f5;
  color: #7b1fa2;
  border-color: #ce93d8;
}

.prop-tag {
  background: #fff3e0;
  color: #e65100;
  border-color: #ffb74d;
  font-size: 12px;
}

.properties-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.property-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.property-label {
  color: #495057;
  font-size: 14px;
  min-width: 120px;
}

.mcp-response-fallback {
  margin-top: 16px;
}

.countdown-timer {
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f4f8 100%);
  border: 2px solid #4a90e2;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
  animation: pulse 2s ease-in-out infinite;
}

.countdown-timer.countdown-finished {
  background: linear-gradient(135deg, #fff3e0 0%, #fff8f0 100%);
  border-color: #ff9800;
  animation: none;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(74, 144, 226, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(74, 144, 226, 0);
  }
}

.countdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.countdown-label {
  font-weight: 600;
  color: #1a1a2e;
  font-size: 14px;
}

.countdown-value {
  font-size: 24px;
  font-weight: 700;
  color: #4a90e2;
  font-variant-numeric: tabular-nums;
}

.countdown-value.countdown-warning {
  color: #ff9800;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.countdown-message {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #ff9800;
  color: #e65100;
  font-weight: 500;
  font-size: 14px;
  text-align: center;
}

.tools-section {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px solid #e9ecef;
}

.tools-section h3 {
  margin-bottom: 20px;
  color: #1a1a2e;
  font-size: 20px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.tool-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.tool-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #4a90e2;
}

.tool-header {
  margin-bottom: 12px;
}

.tool-name {
  margin: 0;
  color: #1a1a2e;
  font-size: 18px;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.tool-description {
  color: #495057;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
}

.tool-parameters {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e9ecef;
}

.tool-parameters strong {
  color: #495057;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: block;
  margin-bottom: 8px;
}

.tool-params-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tool-params-list li {
  padding: 6px 0;
  font-size: 13px;
  color: #6c757d;
  line-height: 1.5;
}

.tool-params-list code {
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  color: #4a90e2;
  font-weight: 600;
  font-size: 12px;
}

.tools-empty {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
  font-size: 16px;
}

.call-tool-section {
  margin-top: 40px;
  padding-top: 30px;
  border-top: 2px solid #e9ecef;
}

.call-tool-section h3 {
  margin-bottom: 20px;
  color: #1a1a2e;
  font-size: 20px;
}

.call-tool-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #f8f9fa;
  padding: 24px;
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.select-input {
  width: 100%;
  padding: 12px;
  background: #ffffff;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #212529;
  cursor: pointer;
  transition: border-color 0.3s;
}

.select-input:focus {
  outline: none;
  border-color: #4a90e2;
}

.select-input:disabled {
  background: #e9ecef;
  cursor: not-allowed;
}

.tool-arguments {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tool-arguments h4 {
  margin: 0 0 12px 0;
  color: #495057;
  font-size: 16px;
  font-weight: 600;
}

.param-type {
  color: #6c757d;
  font-size: 12px;
  font-weight: normal;
  font-family: 'Courier New', monospace;
}

.required {
  color: #ef4444;
  font-weight: 600;
}

.param-description {
  font-size: 12px;
  color: #6c757d;
  margin-bottom: 4px;
  font-style: italic;
}

.input-field {
  width: 100%;
  padding: 10px;
  background: #ffffff;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #212529;
  transition: border-color 0.3s;
}

.input-field:focus {
  outline: none;
  border-color: #4a90e2;
}

.input-field:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
}

.no-arguments {
  padding: 16px;
  background: #e3f2fd;
  border: 1px solid #90caf9;
  border-radius: 8px;
  color: #1976d2;
  font-size: 14px;
  text-align: center;
}

.tool-result {
  margin-top: 24px;
  padding: 20px;
  background: #f0f4f8;
  border: 2px solid #4a90e2;
  border-radius: 12px;
}

.tool-result h4 {
  margin: 0 0 16px 0;
  color: #1a1a2e;
  font-size: 18px;
}

.result-info {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e9ecef;
}

.result-info p {
  margin: 8px 0;
  font-size: 14px;
  color: #495057;
}

.result-content {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 16px;
}

.result-content pre {
  margin: 0;
  color: #f8f9fa;
  font-size: 13px;
  line-height: 1.5;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.retrieval-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 2px solid #e9ecef;
}

.retrieval-tab-button {
  padding: 12px 24px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  font-size: 15px;
  font-weight: 600;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: -2px;
}

.retrieval-tab-button:hover {
  color: #1a1a2e;
  background: #f8f9fa;
}

.retrieval-tab-button.active {
  color: #4a90e2;
  border-bottom-color: #4a90e2;
}

.retrieval-method-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.method-description {
  background: linear-gradient(135deg, #f0f4f8 0%, #ffffff 100%);
  border: 2px solid #e3f2fd;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.method-description h3 {
  margin: 0 0 16px 0;
  color: #1a1a2e;
  font-size: 20px;
}

.method-description p {
  color: #495057;
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 12px;
}

.method-summary {
  color: #495057;
  font-size: 15px;
  line-height: 1.7;
  margin-bottom: 20px;
  font-weight: 500;
}

.query-display {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

.query-display strong {
  display: block;
  color: #1a1a2e;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.query-code {
  background: #1a1a2e;
  color: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Courier New', monospace;
  margin: 0;
  border: 1px solid #e9ecef;
  white-space: pre;
}
</style>

