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
            <div class="retrieval-tab-wrapper">
              <button 
                @click="activeRetrievalMethod = 'openai-agents-with-planning'" 
                :class="['retrieval-tab-button-vertical', { active: activeRetrievalMethod === 'openai-agents-with-planning' }]"
              >
                OpenAI Agents with Planning
              </button>
              <div class="method-tooltip">
                <div class="method-description-tooltip">
                  <h3>OpenAI Agents with Planning</h3>
                  <p class="method-summary">
                    Multi-agent orchestration system that uses a planner-executor pattern. The planner agent generates 5-10 different query strategies, and the execution agent executes each one.
                  </p>
                  <div class="query-display">
                    <strong>How it works:</strong>
                    <ul class="method-features" style="margin-top: 12px;">
                      <li>Planner agent generates 5-10 high-level query strategies</li>
                      <li>Execution agent executes each strategy using MCP tools</li>
                      <li>Returns results from all strategies for comprehensive answers</li>
                      <li>Provides multiple approaches to answer your question</li>
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
                  <div v-if="message.tools_used && message.tools_used.length > 0" class="tools-used">
                    <div class="tools-used-header">
                      <strong>Tools Used:</strong>
                    </div>
                    <div v-for="(tool, toolIndex) in message.tools_used" :key="toolIndex" class="tool-item">
                      <div class="tool-header-row">
                        <span class="tool-name">{{ tool.name }}</span>
                        <span v-if="tool.nested_tools && tool.nested_tools.length > 0" class="nested-tools-badge">
                          {{ tool.nested_tools.length }} nested tool{{ tool.nested_tools.length !== 1 ? 's' : '' }}
                        </span>
                      </div>
                      <details v-if="tool.arguments" class="tool-arguments">
                        <summary>Arguments</summary>
                        <pre>{{ JSON.stringify(tool.arguments, null, 2) }}</pre>
                      </details>
                      <div v-if="tool.nested_tools && tool.nested_tools.length > 0" class="nested-tools">
                        <div class="nested-tools-header">Nested Tools:</div>
                        <div v-for="(nestedTool, nestedIndex) in tool.nested_tools" :key="nestedIndex" class="nested-tool-item">
                          <span class="nested-tool-name">{{ nestedTool.name }}</span>
                          <details v-if="nestedTool.arguments" class="tool-arguments">
                            <summary>Arguments</summary>
                            <pre>{{ JSON.stringify(nestedTool.arguments, null, 2) }}</pre>
                          </details>
                        </div>
                      </div>
                    </div>
                  </div>
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

        <div v-if="activeRetrievalMethod === 'openai-agents-with-planning'" class="retrieval-method-content">
          <div class="card chat-card" :class="{ 'chat-fullscreen': openaiAgentsWithPlanningFullscreen }">
            <div class="chat-header">
              <h3>Ask a Question</h3>
              <div style="display: flex; gap: 8px;">
                <button 
                  @click="clearOpenAIAgentsWithPlanningSession" 
                  class="btn-icon" 
                  title="New Conversation"
                  v-if="openaiAgentsWithPlanningSessionId"
                >
                  🗑️
                </button>
                <button @click="toggleOpenAIAgentsWithPlanningFullscreen" class="btn-icon" :title="openaiAgentsWithPlanningFullscreen ? 'Exit Fullscreen' : 'Fullscreen'">
                  {{ openaiAgentsWithPlanningFullscreen ? '⤓' : '⛶' }}
                </button>
              </div>
            </div>
            <div class="chat-messages" ref="openaiAgentsWithPlanningChatMessages">
              <div v-for="(message, index) in openaiAgentsWithPlanningMessages" :key="index" :class="['chat-message', message.type]">
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
              <div v-if="openaiAgentsWithPlanningLoading" class="chat-message bot typing-indicator">
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
            <form @submit.prevent="askOpenAIAgentWithPlanning" class="chat-form">
              <div class="chat-input-container">
                <textarea
                  v-model="openaiAgentsWithPlanningQuestion"
                  placeholder="Ask a question about the knowledge graph..."
                  class="chat-input"
                  rows="2"
                  :disabled="openaiAgentsWithPlanningLoading"
                ></textarea>
                <button type="submit" :disabled="openaiAgentsWithPlanningLoading || !openaiAgentsWithPlanningQuestion.trim()" class="btn btn-primary chat-send-btn">
                  {{ openaiAgentsWithPlanningLoading ? 'Sending...' : 'Send' }}
                </button>
              </div>
            </form>
          </div>

          <!-- Trace Visualization -->
          <div v-if="latestToolCallGraph" class="card trace-visualization-card">
            <div class="stats-header">
              <h3>Execution Trace</h3>
              <div v-if="latestToolCallGraph.token_usage" class="token-usage-info">
                <span class="token-stat">
                  <strong>Input:</strong> {{ latestToolCallGraph.token_usage.input_tokens || 0 }}
                </span>
                <span class="token-stat">
                  <strong>Output:</strong> {{ latestToolCallGraph.token_usage.output_tokens || 0 }}
                </span>
                <span class="token-stat">
                  <strong>Total:</strong> {{ latestToolCallGraph.token_usage.total_tokens || 0 }}
                </span>
              </div>
            </div>

            <div class="tool-graph-container-retrieval">
              <div class="graph-controls">
                <button @click="zoomIn" class="btn-icon" title="Zoom In">+</button>
                <button @click="zoomOut" class="btn-icon" title="Zoom Out">−</button>
                <button @click="resetZoom" class="btn-icon" title="Reset Zoom">⌂</button>
                <span class="zoom-level">{{ Math.round(graphZoom * 100) }}%</span>
              </div>
              <div class="tool-graph-visualization" 
                   @wheel.prevent="handleWheel"
                   @mousedown="startPan"
                   @mousemove="handlePan"
                   @mouseup="endPan"
                   @mouseleave="endPan">
                <svg :width="fullscreenGraphWidth" 
                     :height="400" 
                     class="tool-graph-svg">
                  <!-- Arrow marker definition -->
                  <defs>
                    <marker id="arrowhead-retrieval" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                      <polygon points="0 0, 10 3, 0 6" fill="#4a90e2" />
                    </marker>
                  </defs>
                  
                  <!-- Transform group for zoom and pan -->
                  <g :transform="`translate(${graphPanX}, ${graphPanY}) scale(${graphZoom})`">
                    <!-- Draw relationships (edges) first so they appear behind nodes -->
                    <g v-for="(rel, relIndex) in latestToolCallGraph.relationships" :key="relIndex">
                      <line
                        :x1="getNodePosition(rel.source, latestToolCallGraph, false).x"
                        :y1="getNodePosition(rel.source, latestToolCallGraph, false).y"
                        :x2="getNodePosition(rel.target, latestToolCallGraph, false).x"
                        :y2="getNodePosition(rel.target, latestToolCallGraph, false).y"
                        class="graph-edge"
                        marker-end="url(#arrowhead-retrieval)"
                      />
                      <text
                        :x="(getNodePosition(rel.source, latestToolCallGraph, false).x + getNodePosition(rel.target, latestToolCallGraph, false).x) / 2"
                        :y="(getNodePosition(rel.source, latestToolCallGraph, false).y + getNodePosition(rel.target, latestToolCallGraph, false).y) / 2 - 5"
                        class="graph-edge-label"
                      >
                        {{ rel.type }}
                      </text>
                    </g>
                    
                    <!-- Draw nodes -->
                    <g v-for="(node, nodeIndex) in latestToolCallGraph.nodes" 
                       :key="nodeIndex"
                       @click.stop="selectNode(node)">
                      <circle
                        :cx="getNodePosition(node.id, latestToolCallGraph, false).x"
                        :cy="getNodePosition(node.id, latestToolCallGraph, false).y"
                        :r="nodeRadius"
                        :class="['graph-node', `graph-node-${node.type}`, { 'graph-node-selected': selectedNode && selectedNode.id === node.id }]"
                      />
                      <text
                        :x="getNodePosition(node.id, latestToolCallGraph, false).x"
                        :y="getNodePosition(node.id, latestToolCallGraph, false).y + nodeRadius + 12"
                        class="graph-node-label"
                        text-anchor="middle"
                      >
                        {{ node.label }}
                      </text>
                    </g>
                  </g>
                </svg>
              </div>
              
              <!-- Node Details Text Area -->
              <div class="node-details-section">
                <h4>Node Details</h4>
                <textarea
                  v-model="nodeDetailsText"
                  readonly
                  class="node-details-textarea"
                  placeholder="Click on a node in the graph above to see its details..."
                  rows="4"
                ></textarea>
              </div>
            </div>

            <!-- Run Query Calls Section -->
            <div v-if="latestRunQueryCalls && latestRunQueryCalls.length > 0" class="run-query-calls-section">
              <h4>Executed Cypher Queries ({{ latestRunQueryCalls.length }})</h4>
              <p class="section-description">All run_query calls intercepted during the latest request execution.</p>
              <div class="run-query-list">
                <div 
                  v-for="(queryCall, index) in latestRunQueryCalls" 
                  :key="index" 
                  class="run-query-item"
                >
                  <div class="run-query-header">
                    <span class="run-query-index">Query #{{ queryCall.index + 1 }}</span>
                    <div class="run-query-header-right">
                      <span v-if="queryCall.context" class="run-query-context">{{ queryCall.context }}</span>
                      <button 
                        v-if="queryCall.result !== null && queryCall.result !== undefined"
                        @click="toggleQueryResult(index)"
                        class="btn-toggle-result"
                        :class="{ 'expanded': expandedQueryResults.has(index) }"
                      >
                        {{ expandedQueryResults.has(index) ? '▼ Hide Result' : '▶ Show Result' }}
                      </button>
                    </div>
                  </div>
                  <pre class="run-query-code">{{ queryCall.query }}</pre>
                  <div 
                    v-if="queryCall.result !== null && queryCall.result !== undefined && expandedQueryResults.has(index)"
                    class="run-query-result"
                  >
                    <div class="run-query-result-header">Result:</div>
                    <pre class="run-query-result-code">{{ formatQueryResult(queryCall.result) }}</pre>
                  </div>
                </div>
              </div>
            </div>
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
      openaiAgentsWithPlanningQuestion: '',
      openaiAgentsWithPlanningLoading: false,
      openaiAgentsWithPlanningMessages: [],
      openaiAgentsWithPlanningSessionId: null,  // Store session ID for conversation continuity
      graphPositionCache: new Map(),  // Cache node positions to prevent recalculation
      graphZoom: 1.0,  // Zoom level for the graph
      graphPanX: 0,  // Pan X offset
      graphPanY: 0,  // Pan Y offset
      isPanning: false,  // Whether user is currently panning
      panStartX: 0,  // Starting X position when panning
      panStartY: 0,  // Starting Y position when panning
      selectedNode: null,  // Currently selected node
      nodeDetailsText: '',  // Formatted node details text
      chatFullscreen: false,
      openaiAgentsFullscreen: false,
      openaiAgentsWithPlanningFullscreen: false,
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
      expandedQueryResults: new Set(),  // Track which query results are expanded
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
    if (this.chatFullscreen || this.openaiAgentsFullscreen || this.openaiAgentsWithPlanningFullscreen) {
      document.body.style.overflow = ''
    }
  },
  watch: {
    latestToolCallGraph() {
      // Clear cache when graph changes to recalculate positions
      this.graphPositionCache.clear()
      // Reset zoom and pan when graph changes
      this.resetZoom()
      // Clear selected node when graph changes
      this.selectedNode = null
      this.nodeDetailsText = ''
    },
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
    },
    openaiAgentsWithPlanningLoading(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          this.scrollOpenAIAgentsWithPlanningChatToBottom()
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
    toggleOpenAIAgentsWithPlanningFullscreen() {
      this.openaiAgentsWithPlanningFullscreen = !this.openaiAgentsWithPlanningFullscreen
      if (this.openaiAgentsWithPlanningFullscreen) {
        document.body.style.overflow = 'hidden'
      } else {
        document.body.style.overflow = ''
      }
    },
    zoomIn() {
      this.graphZoom = Math.min(this.graphZoom * 1.2, 5.0)  // Max zoom 5x
    },
    zoomOut() {
      this.graphZoom = Math.max(this.graphZoom / 1.2, 0.1)  // Min zoom 0.1x
    },
    resetZoom() {
      this.graphZoom = 1.0
      this.graphPanX = 0
      this.graphPanY = 0
    },
    handleWheel(event) {
      const delta = event.deltaY > 0 ? 0.9 : 1.1
      const newZoom = Math.max(0.1, Math.min(5.0, this.graphZoom * delta))
      
      // Zoom towards mouse position
      const rect = event.currentTarget.getBoundingClientRect()
      const mouseX = event.clientX - rect.left
      const mouseY = event.clientY - rect.top
      
      // Calculate zoom point in graph coordinates
      const graphX = (mouseX - this.graphPanX) / this.graphZoom
      const graphY = (mouseY - this.graphPanY) / this.graphZoom
      
      // Adjust pan to keep the point under the mouse fixed
      this.graphPanX = mouseX - graphX * newZoom
      this.graphPanY = mouseY - graphY * newZoom
      
      this.graphZoom = newZoom
    },
    startPan(event) {
      if (event.button === 0) {  // Left mouse button
        this.isPanning = true
        this.panStartX = event.clientX - this.graphPanX
        this.panStartY = event.clientY - this.graphPanY
        event.currentTarget.style.cursor = 'grabbing'
      }
    },
    handlePan(event) {
      if (this.isPanning) {
        this.graphPanX = event.clientX - this.panStartX
        this.graphPanY = event.clientY - this.panStartY
      }
    },
    endPan(event) {
      if (this.isPanning) {
        this.isPanning = false
        if (event.currentTarget) {
          event.currentTarget.style.cursor = 'grab'
        }
      }
    },
    selectNode(node) {
      if (!this.isPanning) {
        this.selectedNode = node
        this.nodeDetailsText = this.formatNodeDetails(node)
      }
    },
    formatNodeDetails(node) {
      if (!node || !node.details) {
        return 'No details available for this node.'
      }
      
      let details = []
      details.push(`Node: ${node.label}`)
      details.push(`Type: ${node.type}`)
      details.push('')
      
      // Function-specific details
      if (node.type === 'function' && node.details.function_name) {
        details.push(`Function Name: ${node.details.function_name}`)
      }
      
      // Handoff-specific details
      if (node.type === 'handoff' && node.details.target_agent) {
        details.push(`Target Agent: ${node.details.target_agent}`)
      }
      
      // Arguments
      if (node.details.arguments) {
        details.push('Arguments:')
        details.push(this.formatValue(node.details.arguments))
        details.push('')
      }
      
      // Result
      if (node.details.result) {
        details.push('Result:')
        details.push(this.formatValue(node.details.result))
        details.push('')
      }
      
      // Message
      if (node.details.message) {
        details.push('Message:')
        details.push(this.formatValue(node.details.message))
        details.push('')
      }
      
      // Response/Content
      if (node.details.response || node.details.content) {
        details.push('Response:')
        details.push(this.formatValue(node.details.response || node.details.content))
        details.push('')
      }
      
      // Prompt
      if (node.details.prompt) {
        details.push('Prompt:')
        details.push(this.formatValue(node.details.prompt))
        details.push('')
      }
      
      // Model
      if (node.details.model) {
        details.push(`Model: ${node.details.model}`)
      }
      
      // Agent Name
      if (node.details.agent_name) {
        details.push(`Agent Name: ${node.details.agent_name}`)
      }
      
      // Tools
      if (node.details.tools) {
        details.push('Tools:')
        details.push(this.formatValue(node.details.tools))
        details.push('')
      }
      
      // Start/Finish times
      if (node.start) {
        details.push(`Start: ${node.start}`)
      }
      if (node.finish) {
        details.push(`Finish: ${node.finish}`)
      }
      
      // Error
      if (node.error) {
        details.push('')
        details.push(`ERROR: ${node.error}`)
      }
      
      return details.join('\n')
    },
    formatValue(value) {
      if (value === null || value === undefined) {
        return ''
      }
      if (typeof value === 'string') {
        return value
      }
      if (typeof value === 'object') {
        try {
          return JSON.stringify(value, null, 2)
        } catch (e) {
          return String(value)
        }
      }
      return String(value)
    },
    scrollOpenAIAgentsWithPlanningChatToBottom() {
      if (this.$refs.openaiAgentsWithPlanningChatMessages) {
        this.$refs.openaiAgentsWithPlanningChatMessages.scrollTop = this.$refs.openaiAgentsWithPlanningChatMessages.scrollHeight
      }
    },
    clearOpenAIAgentsWithPlanningSession() {
      this.openaiAgentsWithPlanningSessionId = null
      this.openaiAgentsWithPlanningMessages = []
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
          time: new Date().toLocaleTimeString(),
          tools_used: response.data.tools_used || []
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
    async askOpenAIAgentWithPlanning() {
      if (!this.openaiAgentsWithPlanningQuestion.trim() || this.openaiAgentsWithPlanningLoading) {
        return
      }

      const userQuestion = this.openaiAgentsWithPlanningQuestion.trim()
      this.openaiAgentsWithPlanningQuestion = ''
      this.openaiAgentsWithPlanningLoading = true

      // Add user message
      const userMessage = {
        type: 'user',
        text: userQuestion,
        time: new Date().toLocaleTimeString()
      }
      this.openaiAgentsWithPlanningMessages.push(userMessage)
      
      // Clear expanded query results for new query
      this.expandedQueryResults.clear()

      // Scroll to bottom to show typing indicator
      this.$nextTick(() => {
        this.scrollOpenAIAgentsWithPlanningChatToBottom()
      })
      
      // Keep scrolling while loading to follow typing indicator
      const scrollInterval = setInterval(() => {
        if (this.openaiAgentsWithPlanningLoading) {
          this.scrollOpenAIAgentsWithPlanningChatToBottom()
        } else {
          clearInterval(scrollInterval)
        }
      }, 100)

      try {
        const response = await axios.post('/api/openai-agents-with-planning/query', {
          question: userQuestion,
          session_id: this.openaiAgentsWithPlanningSessionId  // Send session ID for continuity
        })

        // Store session_id from response if we don't have one yet
        if (!this.openaiAgentsWithPlanningSessionId && response.data.session_id) {
          this.openaiAgentsWithPlanningSessionId = response.data.session_id
        }

        // Add agent response
        const agentMessage = {
          type: 'bot',
          text: response.data.answer || 'No answer provided.',
          time: new Date().toLocaleTimeString(),
          tools_used: response.data.tools_used || [],
          tool_call_graph: response.data.tool_call_graph || null,
          run_query_calls: response.data.run_query_calls || []
        }
        this.openaiAgentsWithPlanningMessages.push(agentMessage)
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.openaiAgentsWithPlanningMessages.push(errorMessage)
      } finally {
        this.openaiAgentsWithPlanningLoading = false
        this.$nextTick(() => {
          this.scrollOpenAIAgentsWithPlanningChatToBottom()
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
    },
    getNodePosition(nodeId, graph, isFullscreen) {
      // Simple layout: arrange nodes in a hierarchical tree structure
      // Cache positions to prevent recalculation on every render
      if (!graph || !graph.nodes) {
        return { x: 100, y: 100 }
      }
      
      // Create a cache key based on graph structure and dimensions
      const graphKey = JSON.stringify({
        nodes: graph.nodes.map(n => n.id).sort(),
        relationships: graph.relationships.map(r => `${r.source}->${r.target}`).sort(),
        width: isFullscreen ? this.fullscreenGraphWidth : this.graphWidth,
        height: isFullscreen ? this.fullscreenGraphHeight : this.graphHeight
      })
      
      // Check cache first
      if (this.graphPositionCache.has(graphKey)) {
        const cachedPositions = this.graphPositionCache.get(graphKey)
        return cachedPositions[nodeId] || { x: 100, y: 100 }
      }
      
      // Calculate positions if not cached
      const nodes = graph.nodes || []
      const relationships = graph.relationships || []
      const width = isFullscreen ? this.fullscreenGraphWidth : this.graphWidth
      const height = isFullscreen ? this.fullscreenGraphHeight : this.graphHeight
      
      // Find root nodes (nodes that are not targets of any relationship)
      const targetNodes = new Set(relationships.map(r => r.target))
      const rootNodes = nodes.filter(n => !targetNodes.has(n.id))
      
      // Simple hierarchical layout
      const nodePositions = {}
      const levelMap = {}
      const visited = new Set()
      
      // Assign levels using BFS
      const queue = []
      rootNodes.forEach(node => {
        levelMap[node.id] = 0
        queue.push(node.id)
        visited.add(node.id)
      })
      
      while (queue.length > 0) {
        const currentId = queue.shift()
        const currentLevel = levelMap[currentId]
        
        relationships
          .filter(r => r.source === currentId)
          .forEach(rel => {
            if (!visited.has(rel.target)) {
              levelMap[rel.target] = currentLevel + 1
              visited.add(rel.target)
              queue.push(rel.target)
            }
          })
      }
      
      // Position nodes by level
      const nodesByLevel = {}
      nodes.forEach(node => {
        const level = levelMap[node.id] || 0
        if (!nodesByLevel[level]) {
          nodesByLevel[level] = []
        }
        nodesByLevel[level].push(node.id)
      })
      
      const maxLevel = Math.max(...Object.keys(nodesByLevel).map(Number), 0)
      const levelHeight = maxLevel > 0 ? height / (maxLevel + 1) : height / 2
      
      Object.keys(nodesByLevel).forEach(level => {
        const levelNodes = nodesByLevel[level]
        const levelY = (parseInt(level) + 1) * levelHeight
        const nodeSpacing = width / (levelNodes.length + 1)
        
        levelNodes.forEach((nodeId, index) => {
          nodePositions[nodeId] = {
            x: (index + 1) * nodeSpacing,
            y: levelY
          }
        })
      })
      
      // Cache the positions
      this.graphPositionCache.set(graphKey, nodePositions)
      
      // Limit cache size to prevent memory issues
      if (this.graphPositionCache.size > 10) {
        const firstKey = this.graphPositionCache.keys().next().value
        this.graphPositionCache.delete(firstKey)
      }
      
      return nodePositions[nodeId] || { x: 100, y: 100 }
    },
    toggleQueryResult(index) {
      if (this.expandedQueryResults.has(index)) {
        this.expandedQueryResults.delete(index)
      } else {
        this.expandedQueryResults.add(index)
      }
      // Force reactivity by creating a new Set
      this.expandedQueryResults = new Set(this.expandedQueryResults)
    },
    formatQueryResult(result) {
      if (result === null || result === undefined) {
        return 'No result'
      }
      if (typeof result === 'string') {
        return result
      }
      if (typeof result === 'object') {
        try {
          return JSON.stringify(result, null, 2)
        } catch (e) {
          return String(result)
        }
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
    },
    graphWidth() {
      return 800
    },
    graphHeight() {
      return 500
    },
    fullscreenGraphWidth() {
      // Use a stable value to prevent reactive updates
      return typeof window !== 'undefined' ? window.innerWidth - 80 : 1200
    },
    fullscreenGraphHeight() {
      // Use a stable value to prevent reactive updates
      return typeof window !== 'undefined' ? window.innerHeight - 120 : 800
    },
    nodeRadius() {
      return 18  // Reduced from 30 to make nodes smaller
    },
    latestToolCallGraph() {
      // Find the most recent tool call graph from messages
      // Iterate backwards to find the latest one
      for (let i = this.openaiAgentsWithPlanningMessages.length - 1; i >= 0; i--) {
        const message = this.openaiAgentsWithPlanningMessages[i]
        if (message.tool_call_graph && message.tool_call_graph.nodes && message.tool_call_graph.nodes.length > 0) {
          return message.tool_call_graph
        }
      }
      return null
    },
    latestRunQueryCalls() {
      // Find the most recent run_query_calls from messages
      // Iterate backwards to find the latest one
      for (let i = this.openaiAgentsWithPlanningMessages.length - 1; i >= 0; i--) {
        const message = this.openaiAgentsWithPlanningMessages[i]
        if (message.run_query_calls && message.run_query_calls.length > 0) {
          return message.run_query_calls
        }
      }
      return []
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

.message.info {
  border-color: #4a90e2;
  background: #f0f4f8;
  padding: 20px;
  border-radius: 8px;
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

.tools-used {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.tools-used-header {
  font-size: 12px;
  font-weight: 600;
  color: #4a90e2;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-tool-graph {
  padding: 4px 12px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #4a90e2;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-tool-graph:hover {
  background: #e9ecef;
  border-color: #4a90e2;
}

.btn-tool-graph.active {
  background: #4a90e2;
  color: white;
  border-color: #4a90e2;
}

.tool-call-graph-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.tool-graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #4a90e2;
}

.tool-graph-container {
  margin: 16px 0;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
  overflow-x: auto;
  transition: all 0.3s ease;
}

.tool-graph-container.tool-graph-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10000;
  margin: 0;
  padding: 20px;
  border-radius: 0;
  background: white;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.trace-visualization-card {
  margin-top: 20px;
}

.trace-visualization-card .stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.trace-visualization-card .stats-header h3 {
  margin: 0;
  color: #1a1a2e;
  font-size: 20px;
}

.tool-graph-container-retrieval {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tool-graph-container-retrieval .node-details-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #dee2e6;
}

.tool-graph-container-retrieval .node-details-section h4 {
  margin: 0 0 8px 0;
  color: #1a1a2e;
  font-size: 16px;
}

.tool-graph-container-retrieval .node-details-textarea {
  min-height: 150px;
  font-size: 12px;
}

.tool-graph-container-retrieval .run-query-calls-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #dee2e6;
}

.tool-graph-container-retrieval .run-query-calls-section h4 {
  margin: 0 0 8px 0;
  color: #1a1a2e;
  font-size: 16px;
}

.tool-graph-container-full {
  margin: 20px 0;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid #dee2e6;
  overflow: hidden;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.graph-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px;
  background: white;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.zoom-level {
  margin-left: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #495057;
  min-width: 50px;
}


.tool-graph-fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e9ecef;
  flex-shrink: 0;
}

.tool-graph-fullscreen-header strong {
  font-size: 18px;
  color: #1a1a2e;
}

.tool-graph-visualization {
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: grab;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.tool-graph-visualization:active {
  cursor: grabbing;
}

.tool-graph-svg {
  border: 1px solid #dee2e6;
  border-radius: 8px;
  background: white;
}

.graph-edge {
  stroke: #4a90e2;
  stroke-width: 2;
  fill: none;
}

.graph-edge-label {
  font-size: 10px;
  fill: #6c757d;
  font-weight: 500;
}

.graph-node {
  stroke: #fff;
  stroke-width: 2;
  cursor: pointer;
  transition: all 0.2s;
}

.graph-node:hover {
  stroke-width: 3;
  filter: brightness(1.1);
}

.graph-node-selected {
  stroke-width: 4;
  stroke: #ff9800;
  filter: brightness(1.2);
}

.graph-node-trace {
  fill: #9c27b0;
}

.graph-node-agent {
  fill: #4a90e2;
}

.graph-node-function {
  fill: #28a745;
}

.graph-node-generation {
  fill: #ff9800;
}

.graph-node-response {
  fill: #00bcd4;
}

.graph-node-mcp_list_tools {
  fill: #4caf50;
}

.graph-node-handoff {
  fill: #e91e63;
}

.graph-node-guardrail {
  fill: #f44336;
}

.graph-node-custom {
  fill: #ffc107;
}

.graph-node-span {
  fill: #6c757d;
}

.graph-node-unknown {
  fill: #6c757d;
}

.graph-node-label {
  font-size: 10px;
  font-weight: 600;
  fill: #1a1a2e;
  pointer-events: none;
}

.node-details-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid #e9ecef;
}

.node-details-section h3 {
  margin: 0 0 12px 0;
  color: #1a1a2e;
  font-size: 18px;
}

.node-details-textarea {
  width: 100%;
  min-height: 300px;
  padding: 16px;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
  resize: vertical;
  color: #1a1a2e;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.node-details-textarea:focus {
  outline: none;
  border-color: #4a90e2;
  background: white;
}

.run-query-calls-section {
  margin-top: 20px;
}

.run-query-calls-section h3 {
  margin-bottom: 12px;
  color: #1a1a2e;
  font-size: 20px;
}

.section-description {
  color: #6c757d;
  font-size: 14px;
  margin-bottom: 20px;
  font-style: italic;
}

.run-query-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.run-query-item {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s ease;
}

.run-query-item:hover {
  border-color: #4a90e2;
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.1);
}

.run-query-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #dee2e6;
}

.run-query-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-toggle-result {
  background: #4a90e2;
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
  font-family: inherit;
}

.btn-toggle-result:hover {
  background: #357abd;
}

.btn-toggle-result.expanded {
  background: #6c757d;
}

.btn-toggle-result.expanded:hover {
  background: #5a6268;
}

.run-query-result {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #dee2e6;
}

.run-query-result-header {
  font-weight: 600;
  color: #28a745;
  font-size: 14px;
  margin-bottom: 8px;
}

.run-query-result-code {
  margin: 0;
  padding: 12px;
  background: #f0f8ff;
  border: 1px solid #b3d9ff;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #212529;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
}

.run-query-index {
  font-weight: 600;
  color: #4a90e2;
  font-size: 14px;
}

.run-query-context {
  font-size: 12px;
  color: #6c757d;
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

.run-query-code {
  margin: 0;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #212529;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.tool-item {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 3px solid #4a90e2;
}

.tool-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.tool-name {
  font-weight: 600;
  color: #1a1a2e;
  font-size: 13px;
}

.nested-tools-badge {
  font-size: 11px;
  font-weight: 600;
  color: #4a90e2;
  background: #e3f2fd;
  padding: 2px 8px;
  border-radius: 12px;
  border: 1px solid #90caf9;
}

.nested-tools {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(74, 144, 226, 0.2);
  padding-left: 16px;
  border-left: 2px solid #90caf9;
}

.nested-tools-header {
  font-size: 11px;
  font-weight: 600;
  color: #495057;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nested-tool-item {
  margin-bottom: 8px;
  padding: 6px 10px;
  background: white;
  border-radius: 6px;
  border-left: 2px solid #90caf9;
}

.nested-tool-name {
  font-weight: 600;
  color: #1976d2;
  font-size: 12px;
}

.tool-arguments {
  margin-top: 6px;
}

.tool-arguments summary {
  font-size: 12px;
  color: #6c757d;
  cursor: pointer;
  user-select: none;
}

.tool-arguments summary:hover {
  color: #4a90e2;
}

.tool-arguments pre {
  margin-top: 6px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  font-size: 11px;
  overflow-x: auto;
  border: 1px solid #dee2e6;
}

.conversation-history-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.btn-conversation-history {
  padding: 6px 12px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #4a90e2;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-conversation-history:hover {
  background: #e9ecef;
  border-color: #4a90e2;
}

.btn-conversation-history.active {
  background: #4a90e2;
  color: white;
  border-color: #4a90e2;
}

.conversation-history-content {
  margin-top: 12px;
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 12px;
  background: #f8f9fa;
}

.conversation-entry {
  margin-bottom: 12px;
  padding: 10px;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #dee2e6;
}

.conversation-entry-user {
  border-left-color: #4a90e2;
}

.conversation-entry-assistant {
  border-left-color: #28a745;
}

.conversation-entry-tool {
  border-left-color: #ffc107;
}

.conversation-entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 600;
}

.conversation-entry-role {
  color: #495057;
}

.conversation-entry-type {
  padding: 2px 8px;
  background: #e9ecef;
  border-radius: 4px;
  color: #6c757d;
  font-size: 10px;
  text-transform: uppercase;
}

.conversation-entry-body {
  margin-top: 8px;
}

.conversation-entry-content {
  margin: 0;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

.tool-call-info {
  font-size: 12px;
}

.tool-call-info strong {
  color: #495057;
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

.token-usage-info {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 8px 16px;
  background: #f0f4f8;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.token-stat {
  font-size: 14px;
  color: #495057;
}

.token-stat strong {
  color: #1a1a2e;
  margin-right: 4px;
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

