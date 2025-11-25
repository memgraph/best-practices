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
        @click="activeTab = 'chat'" 
        :class="['tab-button', { active: activeTab === 'chat' }]"
      >
        Graph Retrieval
      </button>
      <button 
        @click="activeTab = 'stats'" 
        :class="['tab-button', { active: activeTab === 'stats' }]"
      >
        Stats
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

    <main class="main-content chat-content" v-if="activeTab === 'chat'">
      <div class="card chat-card">
        <h2>Ask a Question</h2>
        <div class="chat-messages" ref="chatMessages">
          <div v-for="(message, index) in chatMessages" :key="index" :class="['chat-message', message.type]">
            <div class="message-content">
              <div class="message-header">
                <strong>{{ message.type === 'user' ? 'You' : 'Graph' }}</strong>
                <span class="message-time">{{ message.time }}</span>
              </div>
              <div class="message-text">{{ message.text }}</div>
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
    </main>

    <main class="main-content" v-if="activeTab === 'stats'">
      <div class="card">
        <div class="stats-header">
          <h2>Knowledge Graph Statistics</h2>
          <button @click="fetchStats" :disabled="statsLoading" class="btn btn-primary refresh-btn">
            {{ statsLoading ? 'Loading...' : 'Refresh' }}
          </button>
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
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      activeTab: 'ingest',
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
      stats: null,
      statsLoading: false,
      statsError: ''
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
      }

      this.loading = false
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

      // Scroll to bottom
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

.chat-content {
  max-width: 900px;
  margin: 0 auto;
}

.chat-card {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 250px);
  min-height: 600px;
}

.chat-card h2 {
  margin-bottom: 20px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-message {
  display: flex;
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

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chat-message.user .message-content {
  background: #4a90e2;
  color: white;
}

.chat-message.bot .message-content {
  background: white;
  color: #1a1a2e;
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
  padding: 12px;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  transition: border-color 0.3s;
  color: #212529;
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
</style>

