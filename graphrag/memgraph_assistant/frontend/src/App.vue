<template>
  <div class="app">
    <header class="header">
      <div class="logo-container">
        <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph Logo" class="logo" />
        <h1>Memgraph Assistant</h1>
      </div>
      <p class="subtitle">Documentation-aware chat assistant for Memgraph</p>
    </header>

    <div class="container">
      <div class="tabs">
        <button 
          @click="activeTab = 'ingest'" 
          :class="['tab-button', { active: activeTab === 'ingest' }]"
        >
          Document Ingestion
        </button>
        <button 
          @click="activeTab = 'chat'" 
          :class="['tab-button', { active: activeTab === 'chat' }]"
        >
          Chat Assistant
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

      <!-- Ingestion Tab -->
      <main class="main-content" v-if="activeTab === 'ingest'">
        <div class="card">
          <h2>Documentation Ingestion</h2>
          <p class="description">Scrape and ingest all documentation from memgraph.com/docs</p>
          
          <div v-if="ingestMessage" :class="['message', ingestMessageType]">
            {{ ingestMessage }}
          </div>


          <!-- Custom URLs Ingestion -->
          <div class="card custom-urls-card">
            <h3>Ingest URLs</h3>
            <p class="description">Paste URLs (one per line) to ingest specific documents. Leave empty to ingest all documentation.</p>
            <div class="form-group">
              <textarea
                v-model="customUrls"
                rows="6"
                placeholder="https://memgraph.com/docs/deployment/workloads&#10;https://memgraph.com/docs/deployment/workloads/memgraph-in-cybersecurity"
                class="urls-textarea"
                :disabled="ingesting"
              ></textarea>
            </div>
            
            <div class="batch-options">
              <label class="checkbox-label">
                <input type="checkbox" v-model="scrapeCypherQueries" />
                <span>Scrape Cypher queries</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="batchOnlyChunks" />
                <span>Only create chunks (skip LightRAG processing)</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="batchLinkChunks" />
                <span>Link chunks with NEXT relationship</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="batchCreateVectorIndex" />
                <span>Create vector index</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="batchCreateTextIndex" />
                <span>Create text index</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="batchCleanup" />
                <span>Cleanup existing data</span>
              </label>
            </div>
            
            <button 
              @click="ingestCustomUrls" 
              :disabled="ingesting" 
              class="btn btn-primary"
            >
              {{ ingesting ? 'Ingesting...' : (customUrls.trim() ? 'Ingest URLs' : 'Ingest All Documentation') }}
            </button>
          </div>

          <!-- Discovered URLs Display -->
          <div v-if="discoveredUrls && discoveredUrls.length > 0" class="card discovered-urls-card">
            <div class="urls-header">
              <h3>Discovered URLs</h3>
              <div class="urls-stats">
                <span v-if="urlSearchQuery">
                  Showing {{ filteredUrls.length }} of {{ discoveredUrls.length }}
                </span>
                <span v-else>
                  {{ discoveredUrls.length }} URLs
                </span>
              </div>
            </div>
            <div class="urls-search-container">
              <input
                v-model="urlSearchQuery"
                type="text"
                placeholder="Search URLs..."
                class="urls-search-input"
              />
            </div>
            <div class="urls-list">
              <div v-if="filteredUrls.length === 0" class="url-item-empty">
                No URLs match your search
              </div>
              <div v-for="(url, index) in filteredUrls" :key="index" class="url-item">
                {{ url }}
              </div>
            </div>
          </div>

          <!-- Progress Tracking -->
          <div v-if="progress.length > 0" class="card progress-card">
            <div class="progress-overall-header">
              <h3>Ingestion Progress</h3>
              <div class="progress-overall-stats">
                {{ completedDocuments }} / {{ totalDocuments }} documents completed
              </div>
            </div>
            
            <!-- Overall Progress Bar -->
            <div class="progress-overall-bar-container">
              <div class="progress-overall-bar">
                <div 
                  class="progress-overall-bar-fill" 
                  :style="{ width: overallProgressPercentage + '%' }"
                ></div>
              </div>
              <div class="progress-overall-percentage">
                {{ Math.round(overallProgressPercentage) }}%
              </div>
            </div>
            
            <!-- Countdown Timer -->
            <div v-if="(countdownSeconds > 0 || countdownTimer === 0) && !ingestionFinished" class="countdown-timer" :class="{ 'countdown-finished': countdownTimer === 0 }">
              <div class="countdown-header">
                <span class="countdown-label">⏱️ Estimated Time Remaining</span>
                <span class="countdown-value" :class="{ 'countdown-warning': countdownTimer <= 10 && countdownTimer > 0 }">
                  {{ countdownTimer > 0 ? countdownTimer + ' seconds' : 'Finalizing...' }}
                </span>
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
            </div>
          </div>

          <!-- Ingestion Result -->
          <div v-if="ingestResult" class="card success-card">
            <h3>✅ Ingestion Complete!</h3>
            <p><strong>URLs processed:</strong> {{ ingestResult.urls_processed }}</p>
              <div v-if="ingestResult.urls && ingestResult.urls.length > 0">
                <p><strong>Sample URLs:</strong></p>
                <ul class="url-list">
                  <li v-for="url in ingestResult.urls" :key="url">{{ url }}</li>
                </ul>
              </div>
          </div>
        </div>
      </main>

      <!-- Chat Tab -->
      <main class="main-content chat-layout" v-if="activeTab === 'chat'">
        <div class="chat-panel">
          <div class="card chat-card">
          <div class="chat-header">
          <div class="chat-header-content">
            <div class="mode-selector">
              <div class="mode-toggle">
                <button 
                  @click="chatMode = 'agent'"
                  :class="['mode-btn', 'mode-btn-agent', { active: chatMode === 'agent', disabled: loading }]"
                  :disabled="loading"
                  data-tooltip="Agent Mode: Can execute queries, write operations require approval"
                >
                  <span class="mode-btn-icon">🤖</span>
                  <span class="mode-btn-text">Agent</span>
                </button>
                <button 
                  @click="chatMode = 'ask'"
                  :class="['mode-btn', 'mode-btn-ask', { active: chatMode === 'ask', disabled: loading }]"
                  :disabled="loading"
                  data-tooltip="Ask Mode: Only proposes plans, doesn't execute write operations"
                >
                  <span class="mode-btn-icon">💡</span>
                  <span class="mode-btn-text">Ask</span>
                </button>
              </div>
            </div>
            <div class="chat-title-section">
              <h2>Memgraph Assistant</h2>
              <p class="description">Ask questions about Memgraph or request graph operations</p>
            </div>
          </div>
          </div>
          
          <div class="chat-container">
            <div class="chat-messages" ref="chatMessages">
              <div v-if="messages.length === 0" class="empty-state">
                <div class="empty-icon-wrapper">
                  <svg class="empty-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <h3>Start a conversation</h3>
                <p>Ask questions about Memgraph or request graph operations</p>
              </div>
              <div
                v-for="(msg, index) in messages" 
                :key="index" 
                :class="['chat-message', msg.type]"
              >
                <div v-if="msg.type === 'bot'" class="message-avatar bot-avatar">
                  <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph" />
                </div>
                <div v-if="msg.type === 'user'" class="message-avatar user-avatar">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
                <div class="message-content">
                  <div class="message-header">
                    <strong v-if="msg.type === 'user'">You</strong>
                    <span class="message-time">{{ msg.time }}</span>
                  </div>
                  <div v-if="msg.type === 'temp'" :class="['temp-message', { 'log-message': msg.is_log_message }]">
                    <div class="temp-message-icon">{{ msg.is_log_message ? '📝' : '⚙️' }}</div>
                    <div class="temp-message-content">
                      <strong v-if="!msg.is_log_message">Tool Call</strong><strong v-else>Log Message</strong><span v-if="msg.interceptor_name" class="interceptor-name"> ({{ msg.interceptor_name }})</span><span v-if="!msg.is_log_message">: {{ msg.text }}</span>
                      <div v-if="msg.is_log_message" class="log-message-text">{{ msg.text }}</div>
                      <pre v-if="msg.query && !msg.is_log_message" class="query-preview">{{ msg.query }}</pre>
                    </div>
                  </div>
                  <div v-else-if="msg.type === 'approval'" class="approval-message">
                    <div class="approval-header">
                      <div class="approval-icon">⚠️</div>
                      <div class="approval-title">Write Operation Requires Approval<span v-if="msg.interceptor_name" class="interceptor-name"> ({{ msg.interceptor_name }})</span></div>
                    </div>
                    <div class="approval-text">{{ msg.text }}</div>
                    <pre v-if="msg.query" class="query-preview approval-query">{{ msg.query }}</pre>
                    <div class="approval-actions" v-if="msg.status === 'pending'">
                      <button @click="approveQuery(msg.query)" class="btn btn-approve" :disabled="msg.approving">
                        <span v-if="!msg.approving">✓</span>
                        {{ msg.approving ? 'Approving...' : 'Approve' }}
                      </button>
                      <button @click="rejectQuery(msg.query)" class="btn btn-reject" :disabled="msg.rejecting">
                        <span v-if="!msg.rejecting">✗</span>
                        {{ msg.rejecting ? 'Rejecting...' : 'Reject' }}
                      </button>
                    </div>
                    <div v-else-if="msg.status === 'approved'" class="approval-status approved">
                      <span class="status-icon">✓</span>
                      <span>Approved and executed</span>
                    </div>
                    <div v-else-if="msg.status === 'rejected'" class="approval-status rejected">
                      <span class="status-icon">✗</span>
                      <span>Rejected</span>
                    </div>
                    <div v-if="msg.executionResult" class="execution-result">
                      <div class="execution-result-header">Execution Result</div>
                      <pre>{{ JSON.stringify(msg.executionResult, null, 2) }}</pre>
                    </div>
                  </div>
                  <div v-else class="message-text">
                    <template v-if="msg.type === 'bot' && msg.typing === true">
                      <span>{{ msg.displayText || '' }}</span>
                      <span class="typing-cursor">|</span>
                    </template>
                    <span v-else>{{ msg.text }}</span>
                  </div>
                  <div class="message-footer" v-if="msg.responseTime">
                    <span class="response-time">
                      {{ msg.responseTime }}s
                    </span>
                  </div>
                </div>
              </div>
              <div v-if="loading" class="chat-message bot typing-indicator">
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
            
            <div class="chat-input-container">
              <div class="chat-input-wrapper">
                <textarea
                  v-model="question"
                  @keydown.enter.exact.prevent="sendMessage"
                  @keydown.shift.enter.exact="question += '\n'"
                  :disabled="loading"
                  placeholder="Ask a question or request a graph operation..."
                  class="chat-input"
                  rows="1"
                ></textarea>
                <button 
                  @click="sendMessage" 
                  :disabled="loading || !question.trim()" 
                  class="btn btn-primary chat-send-btn"
                  :class="{ sending: loading }"
                >
                  <span v-if="!loading" class="send-icon">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </span>
                  <span v-else class="sending-spinner"></span>
                  <span class="send-text">{{ loading ? 'Sending...' : 'Send' }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
        </div>
        <div class="graph-panel">
          <GraphVisualization />
        </div>
      </main>

      <!-- Stats Tab -->
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
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">🔗</div>
              <div class="stat-content">
                <div class="stat-label">Entities</div>
                <div class="stat-value">{{ formatNumber(stats.entities) }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">🔀</div>
              <div class="stat-content">
                <div class="stat-label">Relationships</div>
                <div class="stat-value">{{ formatNumber(stats.relationships) }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">📊</div>
              <div class="stat-content">
                <div class="stat-label">Total Nodes</div>
                <div class="stat-value">{{ formatNumber(stats.nodes) }}</div>
              </div>
            </div>
          </div>

          <div v-if="!stats && !statsLoading && !statsError" class="stats-empty">
            <p>Click "Refresh" to load statistics from the knowledge graph.</p>
          </div>
        </div>
      </main>

      <!-- MCP Tab -->
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
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import GraphVisualization from './components/GraphVisualization.vue'

export default {
  name: 'App',
  components: {
    GraphVisualization
  },
  data() {
    return {
      activeTab: 'ingest',
      ingesting: false,
      ingestMessage: '',
      ingestMessageType: '',
      ingestResult: null,
      discoveredUrls: [],
      progress: [],
      countdownTimer: 0,
      customUrls: '',
      scrapeCypherQueries: true,
      batchOnlyChunks: false,
      batchLinkChunks: true,
      batchCreateVectorIndex: true,
      batchCreateTextIndex: true,
      batchCleanup: true,
      countdownSeconds: 0,
      countdownInterval: null,
      ingestionFinished: false,
      question: '',
      loading: false,
      messages: [],
      sessionId: null,
      pendingApprovals: {},
      chatMode: 'agent',  // 'agent' or 'ask' // Map of messageId -> approval data
      urlSearchQuery: '',
      stats: null,
      statsLoading: false,
      statsError: '',
      mcpTesting: false,
      mcpTestResult: null,
      mcpTools: null,
      toolsLoading: false,
      toolsError: ''
    }
  },
  computed: {
    filteredUrls() {
      if (!this.urlSearchQuery) {
        return this.discoveredUrls
      }
      const query = this.urlSearchQuery.toLowerCase()
      return this.discoveredUrls.filter(url => 
        url.toLowerCase().includes(query)
      )
    },
    totalDocuments() {
      return this.progress.length
    },
    completedDocuments() {
      return this.progress.filter(item => item.status === 'completed').length
    },
    overallProgressPercentage() {
      if (this.totalDocuments === 0) return 0
      return (this.completedDocuments / this.totalDocuments) * 100
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
  methods: {
    async ingestCustomUrls() {
      this.ingesting = true
      this.ingestMessage = ''
      this.ingestResult = null
      this.progress = []
      this.ingestionFinished = false
      
      // Clear any existing countdown timer
      if (this.countdownInterval) {
        clearInterval(this.countdownInterval)
        this.countdownInterval = null
      }
      
      try {
        // Parse URLs from textarea (one per line)
        const urlList = this.customUrls
          .split('\n')
          .map(url => url.trim())
          .filter(url => url.length > 0)
        
        // If no URLs provided, backend will automatically discover all documentation
        if (urlList.length === 0) {
          this.ingestMessage = 'No URLs provided, discovering all documentation...'
          this.ingestMessageType = ''
        } else {
          this.ingestMessage = `Processing ${urlList.length} URL(s)...`
          this.ingestMessageType = ''
        }
        
        // Call batch endpoint - it will process all URLs and return when done
        const response = await axios.post('/api/ingest/batch', {
          urls: urlList,
          scrape_cypher_queries: this.scrapeCypherQueries,
          only_chunks: this.batchOnlyChunks,
          link_chunks: this.batchLinkChunks,
          create_vector_index: this.batchCreateVectorIndex,
          create_text_index: this.batchCreateTextIndex,
          cleanup: this.batchCleanup
        })
        
        // Show success message
        this.ingestMessage = response.data.message || `Successfully ingested ${urlList.length} document(s)!`
        this.ingestMessageType = 'success'
        
        // Stop countdown timer and mark as finished
        if (this.countdownInterval) {
          clearInterval(this.countdownInterval)
          this.countdownInterval = null
        }
        this.ingestionFinished = true
        
      } catch (error) {
        this.ingestMessage = error.response?.data?.detail || error.message || 'Error ingesting documents'
        this.ingestMessageType = 'error'
        
        // Stop countdown timer on error
        if (this.countdownInterval) {
          clearInterval(this.countdownInterval)
          this.countdownInterval = null
        }
        this.countdownTimer = null
        this.ingestionFinished = false
      } finally {
        this.ingesting = false
      }
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
    startCountdown() {
      if (this.countdownInterval) {
        clearInterval(this.countdownInterval)
      }
      this.countdownInterval = setInterval(() => {
        if (this.countdownTimer > 0) {
          this.countdownTimer--
        } else {
          clearInterval(this.countdownInterval)
          this.countdownInterval = null
        }
      }, 1000)
    },
    scrollToProgress() {
      this.$nextTick(() => {
        const progressCard = document.querySelector('.progress-card')
        if (progressCard) {
          progressCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      })
    },
    async sendMessage() {
      if (!this.question.trim() || this.loading) {
        return
      }

      const userQuestion = this.question.trim()
      this.question = ''
      this.loading = true

      // Add user message
      this.messages.push({
        type: 'user',
        text: userQuestion,
        time: new Date().toLocaleTimeString()
      })

      this.scrollToBottom()

      try {
        const startTime = performance.now()
        // Use fetch API for SSE streaming
        const response = await fetch('/api/chat/query-stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: userQuestion,
            session_id: this.sessionId,
            mode: this.chatMode
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        let finalResult = null

        // Process SSE stream
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.type === 'result') {
                  finalResult = data.data
                } else if (data.type === 'error') {
                  throw new Error(data.error || 'Unknown error occurred')
                } else if (data.type === 'mcp_tool_call') {
                  // Display MCP tool call message in chat
                  let query = ''
                  let displayText = `Executing ${data.tool_name}`
                  
                  // Handle log_message specially - show the message content
                  let isLogMessage = false
                  if (data.tool_name === 'log_message') {
                    const message = data.data?.arguments?.message || ''
                    displayText = message
                    query = '' // No query for log messages
                    isLogMessage = true
                    console.log('📝 Log message received:', message)
                  } else {
                    // For other tools (like run_query), extract query
                    query = data.data?.arguments?.query || ''
                  }
                  
                  const toolCallMessage = {
                    type: 'temp',
                    text: displayText,
                    interceptor_name: data.interceptor_name,
                    query: query,
                    is_log_message: isLogMessage,
                    time: new Date().toLocaleTimeString()
                  }
                  this.messages.push(toolCallMessage)
                  this.scrollToBottom()
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e)
              }
            }
          }
        }

        if (finalResult) {
          const endTime = performance.now()
          const responseTimeSeconds = (endTime - startTime) / 1000

          // Store session_id
          if (!this.sessionId && finalResult.session_id) {
            this.sessionId = finalResult.session_id
          }

          // Add bot response with typewriter effect
          const fullText = finalResult.answer || 'No answer provided.'
          const botMessage = {
            type: 'bot',
            text: fullText,
            displayText: '',
            typing: true,
            time: new Date().toLocaleTimeString(),
            responseTime: responseTimeSeconds.toFixed(2)
          }
          this.messages.push(botMessage)
          
          // Wait for Vue to update the DOM before starting typewriter effect
          this.$nextTick(() => {
            // Find the message in the array to ensure we're working with the reactive version
            const messageIndex = this.messages.length - 1
            const reactiveMessage = this.messages[messageIndex]
            this.typewriterEffect(reactiveMessage, fullText)
            this.scrollToBottom()
          })
        } else {
          throw new Error('No result received from stream')
        }
      } catch (error) {
        const errorText = error.response?.data?.detail || error.message || 'An error occurred while processing your question.'
        const errorMessage = {
          type: 'bot',
          text: errorText,
          displayText: '',
          typing: true,
          time: new Date().toLocaleTimeString()
        }
        this.messages.push(errorMessage)
        this.typewriterEffect(errorMessage, errorText)
        this.scrollToBottom()
      } finally {
        this.loading = false
      }
    },
    scrollToBottom() {
      this.$nextTick(() => {
        if (this.$refs.chatMessages) {
          this.$refs.chatMessages.scrollTop = this.$refs.chatMessages.scrollHeight
        }
      })
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
        this.mcpTestResult = {
          status: 'success',
          mcp_url: response.data.mcp_url,
          mcp_response: response.data.mcp_response
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
    async approveQuery(query) {
      // Find the message with this query
      const approvalMsg = this.messages.find(msg => msg.query === query && msg.type === 'approval')
      if (!approvalMsg) return
      
      approvalMsg.approving = true
      // Vue 3: reactivity is automatic, $forceUpdate usually not needed
      
      try {
        const response = await axios.post('/api/chat/approve', {
          query: query,
          session_id: this.sessionId
        })
        
        // Update message status
        approvalMsg.status = 'approved'
        approvalMsg.executionResult = response.data.result
        approvalMsg.approving = false
        
        // Remove from pending approvals (Vue 3: use delete operator)
        if (approvalMsg.query_hash) {
          delete this.pendingApprovals[approvalMsg.query_hash]
        }
        
        // Add success message with typewriter effect
        const successText = `✅ Query approved and executed successfully!\n\nResult: ${JSON.stringify(response.data.result, null, 2)}`
        const successMessage = {
          type: 'bot',
          text: successText,
          displayText: '',
          typing: true,
          time: new Date().toLocaleTimeString()
        }
        this.messages.push(successMessage)
        this.typewriterEffect(successMessage, successText)
        
        this.scrollToBottom()
      } catch (error) {
        approvalMsg.approving = false
        approvalMsg.status = 'error'
        approvalMsg.error = error.response?.data?.detail || error.message || 'Failed to approve query'
        
        const errorText = `❌ Error executing approved query: ${error.response?.data?.detail || error.message}`
        const errorMsg = {
          type: 'bot',
          text: errorText,
          displayText: '',
          typing: true,
          time: new Date().toLocaleTimeString()
        }
        this.messages.push(errorMsg)
        this.typewriterEffect(errorMsg, errorText)
        
        this.scrollToBottom()
      }
    },
    async rejectQuery(query) {
      // Find the message with this query
      const approvalMsg = this.messages.find(msg => msg.query === query && msg.type === 'approval')
      if (!approvalMsg) return
      
      approvalMsg.rejecting = true
      // Vue 3: reactivity is automatic, $forceUpdate usually not needed
      
      try {
        await axios.post('/api/chat/reject', {
          query: query,
          session_id: this.sessionId
        })
        
        // Update message status
        approvalMsg.status = 'rejected'
        approvalMsg.rejecting = false
        
        // Remove from pending approvals (Vue 3: use delete operator)
        if (approvalMsg.query_hash) {
          delete this.pendingApprovals[approvalMsg.query_hash]
        }
        
        this.scrollToBottom()
      } catch (error) {
        approvalMsg.rejecting = false
        const rejectErrorText = `❌ Error rejecting query: ${error.response?.data?.detail || error.message}`
        const rejectErrorMsg = {
          type: 'bot',
          text: rejectErrorText,
          displayText: '',
          typing: true,
          time: new Date().toLocaleTimeString()
        }
        this.messages.push(rejectErrorMsg)
        this.typewriterEffect(rejectErrorMsg, rejectErrorText)
        
        this.scrollToBottom()
      }
    },
    typewriterEffect(message, fullText) {
      if (!fullText || fullText.length === 0) {
        // No text to type, just show it immediately
        const messageIndex = this.messages.findIndex(m => m === message)
        if (messageIndex !== -1) {
          this.messages[messageIndex].typing = false
          this.messages[messageIndex].displayText = fullText
        }
        return
      }
      
      let index = 0
      const speed = 15 // milliseconds per character (adjust for faster/slower typing)
      
      // Find the message index in the array to ensure reactivity
      const messageIndex = this.messages.findIndex(m => m === message)
      if (messageIndex === -1) {
        console.warn('Message not found for typewriter effect', message)
        return
      }
      
      // Ensure the message has the typing property set
      if (!this.messages[messageIndex].hasOwnProperty('typing')) {
        this.messages[messageIndex].typing = true
      }
      if (!this.messages[messageIndex].hasOwnProperty('displayText')) {
        this.messages[messageIndex].displayText = ''
      }
      
      const type = () => {
        if (index < fullText.length) {
          // Update the message in the array - Vue 3 handles reactivity automatically
          const currentText = fullText.substring(0, index + 1)
          this.messages[messageIndex].displayText = currentText
          index++
          // Scroll to bottom periodically during typing
          if (index % 10 === 0) {
            this.$nextTick(() => {
              this.scrollToBottom()
            })
          }
          setTimeout(type, speed)
        } else {
          // Finished typing
          this.messages[messageIndex].typing = false
          this.messages[messageIndex].displayText = fullText
          this.$nextTick(() => {
            this.scrollToBottom()
          })
        }
      }
      
      // Start typing immediately
      type()
    }
  },
  beforeUnmount() {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval)
    }
  }
}
</script>

<style scoped>
.query-preview {
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  margin-top: 8px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-width: 100%;
}

.temp-message {
  font-size: 14px;
}

.temp-message.log-message {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border-left: 4px solid #2196f3;
  padding: 12px;
  border-radius: 8px;
  margin: 8px 0;
}

.temp-message.log-message .temp-message-icon {
  color: #2196f3;
  font-size: 20px;
}

.temp-message.log-message .temp-message-content {
  color: #1565c0;
}

.temp-message.log-message .log-message-text {
  margin-top: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
  color: #424242;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.temp-message.log-message .log-message-content {
  margin-top: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
  color: #424242;
  font-size: 13px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-width: 100%;
}

.message-time {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
</style>
