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
                OpenAI Agents with Basic Planning
              </button>
              <div class="method-tooltip">
                <div class="method-description-tooltip">
                  <h3>OpenAI Agents with Basic Planning</h3>
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
            <div class="retrieval-tab-wrapper">
              <button 
                @click="activeRetrievalMethod = 'openai-agents-with-reasoning'" 
                :class="['retrieval-tab-button-vertical', { active: activeRetrievalMethod === 'openai-agents-with-reasoning' }]"
              >
                OpenAI Agents with Reasoning
              </button>
              <div class="method-tooltip">
                <div class="method-description-tooltip">
                  <h3>OpenAI Agents with Reasoning</h3>
                  <p class="method-summary">
                    Advanced multi-agent system with explicit reasoning capabilities. Uses iterative reasoning loops to guide query execution and ensure high-quality answers.
                  </p>
                  <div class="query-display">
                    <strong>How it works:</strong>
                    <ul class="method-features" style="margin-top: 12px;">
                      <li>Planner agent generates 5-10 diverse query strategies</li>
                      <li>Execution agent executes strategies with chain-of-thought reasoning</li>
                      <li>Reasoning agent analyzes results and identifies gaps</li>
                      <li>Iterative loop: Execute → Reason → Decide next steps</li>
                      <li>Quality-focused: Executes fewer, well-reasoned queries</li>
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
                  <div class="message-text markdown-content" v-html="renderMarkdown(message.text)"></div>
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
                  <div class="message-text markdown-content" v-html="renderMarkdown(message.text)"></div>
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
                  <div class="message-text markdown-content" v-html="renderMarkdown(message.text)"></div>
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
                  <strong>Input tokens:</strong> {{ latestToolCallGraph.token_usage.input_tokens || 0 }}
                </span>
                <span class="token-stat">
                  <strong>Output tokens:</strong> {{ latestToolCallGraph.token_usage.output_tokens || 0 }}
                </span>
                <span class="token-stat">
                  <strong>Total tokens:</strong> {{ latestToolCallGraph.token_usage.total_tokens || 0 }}
                </span>
                <span v-if="latestToolCallGraph.response_time_seconds !== undefined" class="token-stat">
                  <strong>Response time:</strong> {{ latestToolCallGraph.response_time_seconds.toFixed(2) }}s
                </span>
                <span v-if="latestRunQueryCalls && latestRunQueryCalls.length > 0" class="token-stat">
                  <strong>Cypher queries:</strong> {{ latestRunQueryCalls.length }}
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
                      <polygon points="0 0, 10 3, 0 6" fill="#FB6E00" />
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

        <div v-if="activeRetrievalMethod === 'openai-agents-with-reasoning'" class="retrieval-method-content">
          <div class="card chat-card" :class="{ 'chat-fullscreen': openaiAgentsWithReasoningFullscreen }">
            <div class="chat-header">
              <h3>Ask a Question (with Reasoning)</h3>
              <div style="display: flex; gap: 8px;">
                <button 
                  @click="clearOpenAIAgentsWithReasoningSession" 
                  class="btn-icon" 
                  title="New Conversation"
                  v-if="openaiAgentsWithReasoningSessionId"
                >
                  🗑️
                </button>
                <button @click="toggleOpenAIAgentsWithReasoningFullscreen" class="btn-icon" :title="openaiAgentsWithReasoningFullscreen ? 'Exit Fullscreen' : 'Fullscreen'">
                  {{ openaiAgentsWithReasoningFullscreen ? '⤓' : '⛶' }}
                </button>
              </div>
            </div>
            <div class="chat-messages" ref="openaiAgentsWithReasoningChatMessages">
              <div v-for="(message, index) in openaiAgentsWithReasoningMessages" :key="message.id || index" :class="['chat-message', message.type, { 'temp-message': message.type === 'temp' || message.type === 'temp_complete' }]">
                <div v-if="message.type === 'bot' || message.type === 'temp' || message.type === 'temp_complete'" class="message-avatar bot-avatar">
                  <img src="https://avatars.githubusercontent.com/u/17707542?s=400&u=fda65e728ea4d5328bdc339ae13fdee45fd6b71e&v=4" alt="Memgraph" />
                </div>
                <div class="message-content">
                  <div class="message-header">
                    <strong>{{ message.type === 'user' ? 'You' : (message.type === 'temp' || message.type === 'temp_complete' ? 'Tool Call' : 'Memgraph Agent') }}</strong>
                    <span class="message-time">{{ message.time }}</span>
                  </div>
                  <div class="message-text markdown-content" v-html="renderMarkdown(message.text)"></div>
                </div>
                <div v-if="message.type === 'user'" class="message-avatar user-avatar">
                  <div class="avatar-placeholder">You</div>
                </div>
              </div>
              <div v-if="openaiAgentsWithReasoningLoading" class="chat-message bot typing-indicator">
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
            <form @submit.prevent="askOpenAIAgentWithReasoning" class="chat-form">
              <div class="chat-input-container">
                <textarea
                  v-model="openaiAgentsWithReasoningQuestion"
                  placeholder="Ask a question about the knowledge graph..."
                  class="chat-input"
                  rows="2"
                  :disabled="openaiAgentsWithReasoningLoading"
                ></textarea>
                <button type="submit" :disabled="openaiAgentsWithReasoningLoading || !openaiAgentsWithReasoningQuestion.trim()" class="btn btn-primary chat-send-btn">
                  {{ openaiAgentsWithReasoningLoading ? 'Sending...' : 'Send' }}
                </button>
              </div>
            </form>
          </div>

          <!-- Trace Visualization -->
          <div v-if="latestToolCallGraphReasoning" class="card trace-visualization-card">
            <div class="stats-header">
              <h3>Execution Trace</h3>
              <div v-if="latestToolCallGraphReasoning.token_usage" class="token-usage-info">
                <span class="token-stat">
                  <strong>Input tokens:</strong> {{ latestToolCallGraphReasoning.token_usage.input_tokens || 0 }}
                </span>
                <span class="token-stat">
                  <strong>Output tokens:</strong> {{ latestToolCallGraphReasoning.token_usage.output_tokens || 0 }}
                </span>
                <span class="token-stat">
                  <strong>Total tokens:</strong> {{ latestToolCallGraphReasoning.token_usage.total_tokens || 0 }}
                </span>
                <span v-if="latestToolCallGraphReasoning.response_time_seconds !== undefined" class="token-stat">
                  <strong>Response time:</strong> {{ latestToolCallGraphReasoning.response_time_seconds.toFixed(2) }}s
                </span>
                <span v-if="latestRunQueryCallsReasoning && latestRunQueryCallsReasoning.length > 0" class="token-stat">
                  <strong>Cypher queries:</strong> {{ latestRunQueryCallsReasoning.length }}
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
                <svg 
                  :width="graphWidth" 
                  :height="graphHeight" 
                  class="tool-graph-svg">
                  <!-- Arrow marker definition -->
                  <defs>
                    <marker id="arrowhead-reasoning" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                      <polygon points="0 0, 10 3, 0 6" fill="#FB6E00" />
                    </marker>
                  </defs>
                  
                  <!-- Transform group for zoom and pan -->
                  <g :transform="`translate(${graphPanX}, ${graphPanY}) scale(${graphZoom})`">
                    <!-- Edges -->
                    <g v-if="latestToolCallGraphReasoning.relationships">
                      <g v-for="(rel, idx) in latestToolCallGraphReasoning.relationships" :key="`rel-${idx}`">
                        <line
                          :x1="getNodePosition(rel.source, latestToolCallGraphReasoning, false).x"
                          :y1="getNodePosition(rel.source, latestToolCallGraphReasoning, false).y"
                          :x2="getNodePosition(rel.target, latestToolCallGraphReasoning, false).x"
                          :y2="getNodePosition(rel.target, latestToolCallGraphReasoning, false).y"
                          class="graph-edge"
                          marker-end="url(#arrowhead-reasoning)"
                          @click="selectedNode = null"
                        />
                        <text
                          v-if="rel.label"
                          :x="(getNodePosition(rel.source, latestToolCallGraphReasoning, false).x + getNodePosition(rel.target, latestToolCallGraphReasoning, false).x) / 2"
                          :y="(getNodePosition(rel.source, latestToolCallGraphReasoning, false).y + getNodePosition(rel.target, latestToolCallGraphReasoning, false).y) / 2 - 5"
                          class="graph-edge-label"
                          text-anchor="middle"
                        >
                          {{ rel.label }}
                        </text>
                      </g>
                    </g>
                    <!-- Nodes -->
                    <g v-if="latestToolCallGraphReasoning.nodes">
                      <g v-for="(node, idx) in latestToolCallGraphReasoning.nodes"
                         :key="`node-group-${idx}`"
                         @click.stop="selectNode(node, latestToolCallGraphReasoning)">
                        <circle
                          :cx="getNodePosition(node.id, latestToolCallGraphReasoning, false).x"
                          :cy="getNodePosition(node.id, latestToolCallGraphReasoning, false).y"
                          :r="nodeRadius"
                          :class="['graph-node', `graph-node-${node.type || 'unknown'}`, { 'graph-node-selected': selectedNode && selectedNode.id === node.id }]"
                        />
                        <text
                          :x="getNodePosition(node.id, latestToolCallGraphReasoning, false).x"
                          :y="getNodePosition(node.id, latestToolCallGraphReasoning, false).y + nodeRadius + 12"
                          class="graph-node-label"
                          text-anchor="middle"
                        >
                          {{ node.label || node.id }}
                        </text>
                      </g>
                    </g>
                  </g>
                </svg>
              </div>

              <!-- Node Details -->
              <div v-if="selectedNode" class="node-details-section">
                <h4>Node Details</h4>
                <textarea
                  :value="nodeDetailsText"
                  readonly
                  class="node-details-textarea"
                ></textarea>
              </div>

              <!-- Run Query Calls Section -->
              <div v-if="latestRunQueryCallsReasoning && latestRunQueryCallsReasoning.length > 0" class="run-query-calls-section">
                <h4>Executed Cypher Queries ({{ latestRunQueryCallsReasoning.length }})</h4>
                <p class="section-description">All run_query calls intercepted during the latest request execution.</p>
                <div class="run-query-list">
                  <div 
                    v-for="(queryCall, index) in latestRunQueryCallsReasoning" 
                    :key="index" 
                    class="run-query-item"
                  >
                    <div class="run-query-header">
                      <span class="run-query-index">Query #{{ queryCall.index + 1 }}</span>
                      <div class="run-query-header-right">
                        <span v-if="queryCall.context" class="run-query-context">{{ queryCall.context }}</span>
                        <button 
                          v-if="queryCall.result !== null && queryCall.result !== undefined"
                          @click="toggleQueryResultReasoning(index)"
                          class="btn-toggle-result"
                          :class="{ 'expanded': expandedQueryResultsReasoning.has(index) }"
                        >
                          {{ expandedQueryResultsReasoning.has(index) ? '▼ Hide Result' : '▶ Show Result' }}
                        </button>
                      </div>
                    </div>
                    <pre class="run-query-code">{{ queryCall.query }}</pre>
                    <div 
                      v-if="queryCall.result !== null && queryCall.result !== undefined && expandedQueryResultsReasoning.has(index)"
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
      openaiAgentsWithReasoningQuestion: '',
      openaiAgentsWithReasoningLoading: false,
      openaiAgentsWithReasoningMessages: [],
      openaiAgentsWithReasoningSessionId: null,  // Store session ID for conversation continuity
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
      openaiAgentsWithReasoningFullscreen: false,
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
      expandedQueryResultsReasoning: new Set(),  // Track which query results are expanded for reasoning
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
    // Render math when component is mounted
    this.$nextTick(() => {
      this.renderAllMath()
    })
  },
  updated() {
    // Render math after any updates
    this.$nextTick(() => {
      this.renderAllMath()
    })
  },
  beforeUnmount() {
    // Clean up countdown interval when component is destroyed
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval)
    }
    // Restore body overflow if in fullscreen
    if (this.chatFullscreen || this.openaiAgentsFullscreen || this.openaiAgentsWithPlanningFullscreen || this.openaiAgentsWithReasoningFullscreen) {
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
    },
    openaiAgentsWithReasoningLoading(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          this.scrollOpenAIAgentsWithReasoningChatToBottom()
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
        // Render math after message is added
        this.$nextTick(() => {
          this.renderAllMath()
          this.scrollChatToBottom()
        })
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.chatMessages.push(errorMessage)
        // Render math after error message is added
        this.$nextTick(() => {
          this.renderAllMath()
          this.scrollChatToBottom()
        })
      } finally {
        this.chatLoading = false
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
    toggleOpenAIAgentsWithReasoningFullscreen() {
      this.openaiAgentsWithReasoningFullscreen = !this.openaiAgentsWithReasoningFullscreen
      if (this.openaiAgentsWithReasoningFullscreen) {
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
    scrollOpenAIAgentsWithReasoningChatToBottom() {
      if (this.$refs.openaiAgentsWithReasoningChatMessages) {
        this.$refs.openaiAgentsWithReasoningChatMessages.scrollTop = this.$refs.openaiAgentsWithReasoningChatMessages.scrollHeight
      }
    },
    clearOpenAIAgentsWithPlanningSession() {
      this.openaiAgentsWithPlanningSessionId = null
      this.openaiAgentsWithPlanningMessages = []
    },
    clearOpenAIAgentsWithReasoningSession() {
      this.openaiAgentsWithReasoningSessionId = null
      this.openaiAgentsWithReasoningMessages = []
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
        // Render math after message is added
        this.$nextTick(() => {
          this.renderAllMath()
          this.scrollOpenAIAgentsChatToBottom()
        })
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.openaiAgentsMessages.push(errorMessage)
        // Render math after error message is added
        this.$nextTick(() => {
          this.renderAllMath()
          this.scrollOpenAIAgentsChatToBottom()
        })
      } finally {
        this.openaiAgentsLoading = false
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
        const startTime = performance.now()
        const response = await axios.post('/api/openai-agents-with-planning/query', {
          question: userQuestion,
          session_id: this.openaiAgentsWithPlanningSessionId  // Send session ID for continuity
        })
        const endTime = performance.now()
        const responseTimeSeconds = (endTime - startTime) / 1000

        // Store session_id from response if we don't have one yet
        if (!this.openaiAgentsWithPlanningSessionId && response.data.session_id) {
          this.openaiAgentsWithPlanningSessionId = response.data.session_id
        }

        // Add response time to tool_call_graph if it exists
        let toolCallGraph = response.data.tool_call_graph || null
        if (toolCallGraph) {
          toolCallGraph.response_time_seconds = responseTimeSeconds
        }

        // Add agent response
        const agentMessage = {
          type: 'bot',
          text: response.data.answer || 'No answer provided.',
          time: new Date().toLocaleTimeString(),
          tools_used: response.data.tools_used || [],
          tool_call_graph: toolCallGraph,
          run_query_calls: response.data.run_query_calls || []
        }
        this.openaiAgentsWithPlanningMessages.push(agentMessage)
        // Render math after message is added
        this.$nextTick(() => {
          this.renderAllMath()
          this.scrollOpenAIAgentsWithPlanningChatToBottom()
        })
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.openaiAgentsWithPlanningMessages.push(errorMessage)
        // Render math after error message is added
        this.$nextTick(() => {
          this.renderAllMath()
          this.scrollOpenAIAgentsWithPlanningChatToBottom()
        })
      } finally {
        this.openaiAgentsWithPlanningLoading = false
      }
    },
    async askOpenAIAgentWithReasoning() {
      if (!this.openaiAgentsWithReasoningQuestion.trim() || this.openaiAgentsWithReasoningLoading) {
        return
      }

      const userQuestion = this.openaiAgentsWithReasoningQuestion.trim()
      this.openaiAgentsWithReasoningQuestion = ''
      this.openaiAgentsWithReasoningLoading = true

      // Add user message
      const userMessage = {
        type: 'user',
        text: userQuestion,
        time: new Date().toLocaleTimeString()
      }
      this.openaiAgentsWithReasoningMessages.push(userMessage)
      
      // Clear expanded query results for new query
      this.expandedQueryResultsReasoning.clear()

      // Scroll to bottom to show typing indicator
      this.$nextTick(() => {
        this.scrollOpenAIAgentsWithReasoningChatToBottom()
      })
      
      // Keep scrolling while loading to follow typing indicator
      const scrollInterval = setInterval(() => {
        if (this.openaiAgentsWithReasoningLoading) {
          this.scrollOpenAIAgentsWithReasoningChatToBottom()
        } else {
          clearInterval(scrollInterval)
        }
      }, 100)

      try {
        const startTime = performance.now()
        // Use fetch API for SSE streaming
        const response = await fetch('/api/openai-agents-with-reasoning/query-stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: userQuestion,
            session_id: this.openaiAgentsWithReasoningSessionId
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        // Track tool calls - each creates its own message bubble
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
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.type === 'tool_call') {
                  // Create a new message bubble only for tool_call_start events
                  const toolData = data.data
                  
                  // Only create bubbles for start events, ignore complete events
                  if (toolData.type === 'tool_call_start') {
                    // Use the full message which includes the complete query
                    const toolCallMsg = {
                      id: Date.now() + Math.random(), // Unique ID for each message
                      type: 'temp',
                      text: toolData.message || `Calling ${toolData.tool_name}...`,
                      time: new Date().toLocaleTimeString(),
                      tool_name: toolData.tool_name,
                      query: toolData.query
                    }
                    this.openaiAgentsWithReasoningMessages.push(toolCallMsg)
                    this.$nextTick(() => {
                      this.scrollOpenAIAgentsWithReasoningChatToBottom()
                      this.renderAllMath()
                    })
                  }
                  // Ignore tool_call_complete events - no message needed
                } else if (data.type === 'result') {
                  finalResult = data.data
                } else if (data.type === 'error') {
                  throw new Error(data.error || 'Unknown error occurred')
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

          // Store session_id from response if we don't have one yet
          if (!this.openaiAgentsWithReasoningSessionId && finalResult.session_id) {
            this.openaiAgentsWithReasoningSessionId = finalResult.session_id
          }

          // Add response time to tool_call_graph if it exists
          let toolCallGraph = finalResult.tool_call_graph || null
          if (toolCallGraph) {
            toolCallGraph.response_time_seconds = responseTimeSeconds
          }

          // Add agent response
          const agentMessage = {
            type: 'bot',
            text: finalResult.answer || 'No answer provided.',
            time: new Date().toLocaleTimeString(),
            tools_used: finalResult.tools_used || [],
            tool_call_graph: toolCallGraph,
            run_query_calls: finalResult.run_query_calls || []
          }
          this.openaiAgentsWithReasoningMessages.push(agentMessage)
          // Render math after adding the message
          this.$nextTick(() => {
            this.renderAllMath()
            this.scrollOpenAIAgentsWithReasoningChatToBottom()
          })
        } else {
          throw new Error('No result received from stream')
        }
      } catch (error) {
        const errorMessage = {
          type: 'bot',
          text: error.response?.data?.detail || error.message || 'An error occurred while processing your question.',
          time: new Date().toLocaleTimeString()
        }
        this.openaiAgentsWithReasoningMessages.push(errorMessage)
        this.$nextTick(() => {
          this.renderAllMath()
        })
      } finally {
        this.openaiAgentsWithReasoningLoading = false
        this.$nextTick(() => {
          this.scrollOpenAIAgentsWithReasoningChatToBottom()
        })
      }
    },
    renderMarkdown(text) {
      if (!text) return ''
      
      // Extract LaTeX math blocks (both display \[...\] and inline \(...\)) first before any processing
      const mathBlocks = []
      let mathIndex = 0
      
      // Extract display math blocks \[...\]
      let html = text.replace(/\\\[([\s\S]*?)\\\]/g, (match, content) => {
        const placeholder = `__MATH_DISPLAY_${mathIndex}__`
        mathBlocks.push({ type: 'display', content: content.trim() })
        mathIndex++
        return placeholder
      })
      
      // Extract inline math blocks \(...\)
      html = html.replace(/\\\(([\s\S]*?)\\\)/g, (match, content) => {
        const placeholder = `__MATH_INLINE_${mathIndex}__`
        mathBlocks.push({ type: 'inline', content: content.trim() })
        mathIndex++
        return placeholder
      })
      
      // Escape HTML to prevent XSS (but preserve math placeholders)
      // Don't escape the placeholders themselves
      html = html
        .replace(/&(?!amp;|lt;|gt;|quot;|#)/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
      
      // Code blocks (```code```) - handle before inline code
      html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      
      // Inline code (`code`) - but not inside code blocks or math blocks
      html = html.replace(/`([^`\n]+?)`/g, '<code>$1</code>')
      
      // Headers (# Header)
      html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>')
      html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>')
      html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>')
      
      // Lists (- item) - wrap consecutive list items in ul
      const lines = html.split('\n')
      const processedLines = []
      let inList = false
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        // Skip processing if this line contains a math placeholder
        if (line.includes('__MATH_')) {
          processedLines.push(line)
          continue
        }
        if (line.match(/^- (.+)$/)) {
          if (!inList) {
            processedLines.push('<ul>')
            inList = true
          }
          processedLines.push(line.replace(/^- (.+)$/, '<li>$1</li>'))
        } else {
          if (inList) {
            processedLines.push('</ul>')
            inList = false
          }
          processedLines.push(line)
        }
      }
      if (inList) {
        processedLines.push('</ul>')
      }
      html = processedLines.join('\n')
      
      // Bold (**text**)
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      
      // Italic (*text*) - but not bold
      html = html.replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>')
      
      // Line breaks (but preserve existing <br> from code blocks and don't break math blocks)
      // Don't replace \n inside math placeholders
      html = html.replace(/\n/g, '<br>')
      
      // Restore LaTeX math blocks AFTER all other processing (unescaped, KaTeX will render them)
      // Use a more unique placeholder to avoid conflicts
      mathBlocks.forEach((mathBlock, index) => {
        const placeholder = mathBlock.type === 'display' ? `__MATH_DISPLAY_${index}__` : `__MATH_INLINE_${index}__`
        const restored = mathBlock.type === 'display' 
          ? `\\[${mathBlock.content}\\]` 
          : `\\(${mathBlock.content}\\)`
        // Replace all occurrences of the placeholder (in case it appears multiple times)
        html = html.split(placeholder).join(restored)
      })
      
      return html
    },
    renderAllMath() {
      // Render KaTeX math in all markdown content elements
      if (typeof window.renderMathInElement === 'undefined') {
        console.warn('KaTeX renderMathInElement not available. Make sure KaTeX auto-render is loaded.')
        // Try to wait a bit and retry if KaTeX is still loading
        setTimeout(() => {
          if (typeof window.renderMathInElement !== 'undefined') {
            this.renderAllMath()
          }
        }, 500)
        return
      }
      
      this.$nextTick(() => {
        // Use setTimeout to ensure DOM is fully updated
        setTimeout(() => {
          const mathElements = document.querySelectorAll('.markdown-content')
          mathElements.forEach(element => {
            try {
              // Skip if this element already has rendered math (to avoid re-rendering)
              const hasRenderedMath = element.querySelector('.katex')
              if (hasRenderedMath) {
                // Check if there's unrendered math by looking at text content
                const textContent = element.textContent || ''
                const hasUnrenderedDelimiters = textContent.includes('\\[') || textContent.includes('\\(')
                if (!hasUnrenderedDelimiters) {
                  return // All math is already rendered
                }
              }
              
              // Get the text content to check for math delimiters
              const textContent = element.textContent || ''
              const htmlContent = element.innerHTML || ''
              
              // Check for math delimiters in the actual content
              // Look for the literal backslash patterns that KaTeX expects
              const hasMath = textContent.includes('\\[') || textContent.includes('\\(') ||
                             htmlContent.includes('\\[') || htmlContent.includes('\\(')
              
              if (hasMath) {
                // Render math - KaTeX will handle already-rendered elements via ignoredClasses
                window.renderMathInElement(element, {
                  delimiters: [
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false}
                  ],
                  throwOnError: false,
                  strict: false,
                  output: 'html',
                  ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
                  ignoredClasses: ['katex', 'katex-display']
                })
              }
            } catch (e) {
              console.error('Error rendering math in element:', e, element)
            }
          })
        }, 300)
      })
    },
    renderMathInElement(element) {
      // Render KaTeX math after DOM update
      if (typeof window.renderMathInElement !== 'undefined' && element) {
        this.$nextTick(() => {
          setTimeout(() => {
            try {
              // Get the raw HTML content to check for math delimiters
              const htmlContent = element.innerHTML || ''
              const hasUnrenderedMath = htmlContent.includes('\\[') || htmlContent.includes('\\(')
              
              // Check if math has already been rendered
              const hasRenderedMath = element.querySelector('.katex')
              
              // Only render if there's unrendered math and it hasn't been rendered yet
              if (hasUnrenderedMath && !hasRenderedMath) {
                window.renderMathInElement(element, {
                  delimiters: [
                    {left: '\\[', right: '\\]', display: true},
                    {left: '\\(', right: '\\)', display: false}
                  ],
                  throwOnError: false,
                  strict: false,
                  output: 'html'
                })
              }
            } catch (e) {
              console.error('Error rendering math:', e)
            }
          }, 100)
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
    toggleQueryResultReasoning(index) {
      if (this.expandedQueryResultsReasoning.has(index)) {
        this.expandedQueryResultsReasoning.delete(index)
      } else {
        this.expandedQueryResultsReasoning.add(index)
      }
      // Force reactivity by creating a new Set
      this.expandedQueryResultsReasoning = new Set(this.expandedQueryResultsReasoning)
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
    },
    latestToolCallGraphReasoning() {
      // Find the most recent tool call graph from reasoning messages
      for (let i = this.openaiAgentsWithReasoningMessages.length - 1; i >= 0; i--) {
        const message = this.openaiAgentsWithReasoningMessages[i]
        if (message.tool_call_graph && message.tool_call_graph.nodes && message.tool_call_graph.nodes.length > 0) {
          return message.tool_call_graph
        }
      }
      return null
    },
    latestRunQueryCallsReasoning() {
      // Find the most recent run_query_calls from reasoning messages
      for (let i = this.openaiAgentsWithReasoningMessages.length - 1; i >= 0; i--) {
        const message = this.openaiAgentsWithReasoningMessages[i]
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
  color: #231F20;
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
  border-radius: 8px;
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
  color: #231F20;
  font-family: 'Inter', sans-serif;
}

.subtitle {
  font-size: 1.2rem;
  opacity: 0.8;
  color: #646265;
  font-weight: 400;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.card h2 {
  margin-bottom: 20px;
  color: #231F20;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.card h3 {
  margin-bottom: 10px;
  color: #231F20;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
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
  font-weight: 400;
  color: #231F20;
}

.textarea {
  width: 100%;
  padding: 12px;
  background: #FFFFFF;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  font-weight: 400;
  resize: vertical;
  transition: border-color 0.3s;
  color: #231F20;
}

.textarea:focus {
  outline: none;
  border-color: #FB6E00;
}

.estimate-info {
  background: #F9F9F9;
  border: 1px solid #FB6E00;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
}

.estimate-summary {
  font-size: 14px;
  color: #231F20;
  font-weight: 400;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.estimate-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 13px;
}

.estimate-url {
  color: #646265;
  font-weight: 400;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 12px;
}

.estimate-details {
  color: #231F20;
  font-weight: 400;
  white-space: nowrap;
}

.progress-card {
  margin-top: 20px;
}

.progress-item {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
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
  color: #231F20;
  font-size: 14px;
  font-weight: 400;
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
  border-radius: 6px;
  text-transform: uppercase;
}

.progress-status.processing {
  background: #F9F9F9;
  color: #FB6E00;
  border: 1px solid #FB6E00;
}

.progress-status.completed {
  background: #F9F9F9;
  color: #231F20;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.progress-status.error {
  background: #F9F9F9;
  color: #DC2223;
  border: 1px solid #DC2223;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #F9F9F9;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(30deg, #FFC500 0%, #DC2223 41%, #720096 100%);
  transition: width 0.3s ease;
}

.progress-time {
  font-size: 12px;
  color: #646265;
  font-weight: 400;
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
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: linear-gradient(30deg, #FFC500 0%, #DC2223 41%, #720096 100%);
  color: #FFFFFF;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(251, 110, 0, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message {
  border-left: 4px solid;
}

.message h3 {
  color: #231F20;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.message p {
  color: #231F20;
  font-weight: 400;
}

.message.success {
  border-color: #FB6E00;
  background: #FFFFFF;
}

.message.error {
  border-color: #DC2223;
  background: #FFFFFF;
}

.message.info {
  border-color: #FB6E00;
  background: #FFFFFF;
  padding: 20px;
  border-radius: 6px;
}

.status {
  background: #FFFFFF;
}

.status pre {
  background: #231F20;
  color: #FFFFFF;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  border: 1px solid rgba(0, 0, 0, 0.1);
  font-family: 'Inter', monospace;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 2px solid rgba(0, 0, 0, 0.08);
}

.tab-button {
  padding: 12px 24px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  font-size: 16px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #646265;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: -2px;
}

.tab-button:hover {
  color: #231F20;
  background: #F9F9F9;
}

.tab-button.active {
  color: #FB6E00;
  border-bottom-color: #FB6E00;
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
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
}

.retrieval-sidebar h2 {
  margin: 0 0 24px 0;
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
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
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #646265;
  cursor: pointer;
  transition: all 0.3s;
  text-align: left;
  width: 100%;
}

.retrieval-tab-button-vertical:hover {
  color: #231F20;
  background: #F9F9F9;
  border-color: rgba(0, 0, 0, 0.1);
}

.retrieval-tab-button-vertical.active {
  color: #FB6E00;
  background: #FFFFFF;
  border-color: #FB6E00;
  box-shadow: 0 2px 4px rgba(251, 110, 0, 0.1);
}

.method-tooltip {
  position: absolute;
  left: calc(100% + 16px);
  top: 0;
  width: 400px;
  max-height: 80vh;
  overflow-y: auto;
  background: #FFFFFF;
  border: 2px solid #FB6E00;
  border-radius: 8px;
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
  color: #231F20;
  font-size: 18px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.method-description-tooltip .method-summary {
  margin: 0 0 16px 0;
  color: #646265;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
}

.method-description-tooltip .query-display {
  margin-top: 16px;
}

.method-description-tooltip .query-display strong {
  display: block;
  margin-bottom: 8px;
  color: #231F20;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.method-description-tooltip .query-code {
  background: #231F20;
  color: #FFFFFF;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
  overflow-x: auto;
  margin: 0;
  border: 1px solid rgba(0, 0, 0, 0.1);
  font-family: 'Inter', monospace;
}

.method-description-tooltip .method-features {
  margin: 0;
  padding-left: 20px;
  color: #646265;
  font-size: 14px;
  font-weight: 400;
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
  border-bottom: 2px solid rgba(0, 0, 0, 0.08);
}

.chat-header h3 {
  margin: 0;
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.btn-icon {
  background: #F9F9F9;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.3s;
  color: #646265;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 40px;
}

.btn-icon:hover {
  background: #FFFFFF;
  border-color: #FB6E00;
  color: #FB6E00;
  transform: scale(1.05);
}

.chat-card h2 {
  margin-bottom: 20px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #FFFFFF;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05);
}

.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #F9F9F9;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #646265;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #231F20;
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
  border: 2px solid rgba(0, 0, 0, 0.08);
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
  background: linear-gradient(30deg, #FFC500 0%, #DC2223 41%, #720096 100%);
  color: #FFFFFF;
  font-weight: 600;
  font-size: 14px;
  font-family: 'Inter', sans-serif;
}

.typing-indicator {
  opacity: 0.8;
}

.typing-content {
  padding: 16px 20px;
  background: #FFFFFF;
  border-bottom-left-radius: 4px;
  border-left: 3px solid #FB6E00;
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
  background: #FB6E00;
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
  border-radius: 8px;
  background: #FFFFFF;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease;
}

.message-content:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.chat-message.user .message-content {
  background: linear-gradient(30deg, #FFC500 0%, #DC2223 41%, #720096 100%);
  color: #FFFFFF;
  border-bottom-right-radius: 4px;
}

.chat-message.bot .message-content {
  background: #FFFFFF;
  color: #231F20;
  border-bottom-left-radius: 4px;
  border-left: 3px solid #FB6E00;
}

.chat-message.temp .message-content,
.chat-message.temp-message .message-content {
  background: #F9F9F9;
  color: #231F20;
  border-bottom-left-radius: 4px;
  border-left: 3px solid #FB6E00;
  font-style: italic;
  opacity: 0.8;
  padding: 8px 12px;
  max-width: 70%;
  font-size: 0.85em;
}

.chat-message.temp .message-header,
.chat-message.temp-message .message-header {
  color: #FB6E00;
  font-size: 0.85em;
  margin-bottom: 4px;
}

.chat-message.temp .message-text,
.chat-message.temp-message .message-text {
  font-size: 0.85em;
  line-height: 1.4;
}

.chat-message.temp .message-avatar,
.chat-message.temp-message .message-avatar {
  width: 24px;
  height: 24px;
}

.chat-message.temp .message-avatar img,
.chat-message.temp-message .message-avatar img {
  width: 24px;
  height: 24px;
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

.markdown-content {
  white-space: normal;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3 {
  margin: 12px 0 8px 0;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #231F20;
}

.markdown-content h1 {
  font-size: 1.3em;
}

.markdown-content h2 {
  font-size: 1.2em;
}

.markdown-content h3 {
  font-size: 1.1em;
}

.markdown-content code {
  background: #F9F9F9;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Inter', monospace;
  font-size: 0.9em;
  font-weight: 400;
  color: #231F20;
}

.markdown-content pre {
  background: #F9F9F9;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-content pre code {
  background: none;
  padding: 0;
}

.markdown-content ul {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content li {
  margin: 4px 0;
}

.markdown-content strong {
  font-weight: 600;
  color: #231F20;
}

.markdown-content em {
  font-style: italic;
}

.markdown-content .katex-display {
  margin: 12px 0;
  padding: 8px;
  background: #F9F9F9;
  border-left: 3px solid #FB6E00;
  overflow-x: auto;
}

.markdown-content .katex {
  font-size: 1.1em;
}

.tools-used {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.tools-used-header {
  font-size: 12px;
  font-weight: 600;
  color: #FB6E00;
  font-family: 'Inter', sans-serif;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-tool-graph {
  padding: 4px 12px;
  background: #F9F9F9;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-tool-graph:hover {
  background: #FFFFFF;
  border-color: #FB6E00;
}

.btn-tool-graph.active {
  background: linear-gradient(30deg, #FFC500 0%, #DC2223 41%, #720096 100%);
  color: #FFFFFF;
  border-color: #FB6E00;
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
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
}

.tool-graph-container {
  margin: 16px 0;
  padding: 16px;
  background: #F9F9F9;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
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
  background: #FFFFFF;
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
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.tool-graph-container-retrieval {
  margin-top: 16px;
  padding: 16px;
  background: #F9F9F9;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tool-graph-container-retrieval .node-details-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.tool-graph-container-retrieval .node-details-section h4 {
  margin: 0 0 8px 0;
  color: #231F20;
  font-size: 16px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.tool-graph-container-retrieval .node-details-textarea {
  min-height: 150px;
  font-size: 12px;
}

.tool-graph-container-retrieval .run-query-calls-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.tool-graph-container-retrieval .run-query-calls-section h4 {
  margin: 0 0 8px 0;
  color: #231F20;
  font-size: 16px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.tool-graph-container-full {
  margin: 20px 0;
  padding: 20px;
  background: #F9F9F9;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.1);
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
  background: #FFFFFF;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.zoom-level {
  margin-left: 8px;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #231F20;
  min-width: 50px;
}


.tool-graph-fullscreen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.tool-graph-fullscreen-header strong {
  font-size: 18px;
  color: #231F20;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
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
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  background: #FFFFFF;
}

.graph-edge {
  stroke: #FB6E00;
  stroke-width: 2;
  fill: none;
}

.graph-edge-label {
  font-size: 10px;
  fill: #646265;
  font-weight: 400;
  font-family: 'Inter', sans-serif;
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
  fill: #FB6E00;
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
  fill: #646265;
}

.graph-node-unknown {
  fill: #646265;
}

.graph-node-label {
  font-size: 10px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  fill: #231F20;
  pointer-events: none;
}

.node-details-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid rgba(0, 0, 0, 0.08);
}

.node-details-section h3 {
  margin: 0 0 12px 0;
  color: #231F20;
  font-size: 18px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.node-details-textarea {
  width: 100%;
  min-height: 300px;
  padding: 16px;
  background: #F9F9F9;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  font-size: 13px;
  font-family: 'Inter', monospace;
  font-weight: 400;
  resize: vertical;
  color: #231F20;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.node-details-textarea:focus {
  outline: none;
  border-color: #FB6E00;
  background: #FFFFFF;
}

.run-query-calls-section {
  margin-top: 20px;
}

.run-query-calls-section h3 {
  margin-bottom: 12px;
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.section-description {
  color: #646265;
  font-size: 14px;
  font-weight: 400;
  margin-bottom: 20px;
  font-style: italic;
}

.run-query-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.run-query-item {
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 16px;
  transition: all 0.2s ease;
}

.run-query-item:hover {
  border-color: #FB6E00;
  box-shadow: 0 2px 8px rgba(251, 110, 0, 0.1);
}

.run-query-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.run-query-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-toggle-result {
  background: #FB6E00;
  color: #FFFFFF;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-toggle-result:hover {
  background: #DC2223;
}

.btn-toggle-result.expanded {
  background: #646265;
}

.btn-toggle-result.expanded:hover {
  background: #231F20;
}

.run-query-result {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.run-query-result-header {
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #231F20;
  font-size: 14px;
  margin-bottom: 8px;
}

.run-query-result-code {
  margin: 0;
  padding: 12px;
  background: #F9F9F9;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-family: 'Inter', monospace;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.6;
  color: #231F20;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
}

.run-query-index {
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  font-size: 14px;
}

.run-query-context {
  font-size: 12px;
  font-weight: 400;
  color: #646265;
  background: #F9F9F9;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Inter', monospace;
}

.run-query-code {
  margin: 0;
  padding: 12px;
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-family: 'Inter', monospace;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.6;
  color: #231F20;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.tool-item {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #FFFFFF;
  border-radius: 6px;
  border-left: 3px solid #FB6E00;
}

.tool-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.tool-name {
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #231F20;
  font-size: 13px;
}

.nested-tools-badge {
  font-size: 11px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  background: #F9F9F9;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid #FB6E00;
}

.nested-tools {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(251, 110, 0, 0.2);
  padding-left: 16px;
  border-left: 2px solid #FB6E00;
}

.nested-tools-header {
  font-size: 11px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #231F20;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nested-tool-item {
  margin-bottom: 8px;
  padding: 6px 10px;
  background: #FFFFFF;
  border-radius: 4px;
  border-left: 2px solid #FB6E00;
}

.nested-tool-name {
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  font-size: 12px;
}

.tool-arguments {
  margin-top: 6px;
}

.tool-arguments summary {
  font-size: 12px;
  font-weight: 400;
  color: #646265;
  cursor: pointer;
  user-select: none;
}

.tool-arguments summary:hover {
  color: #FB6E00;
}

.tool-arguments pre {
  margin-top: 6px;
  padding: 8px;
  background: #FFFFFF;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 400;
  overflow-x: auto;
  border: 1px solid rgba(0, 0, 0, 0.1);
  font-family: 'Inter', monospace;
}

.conversation-history-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}

.btn-conversation-history {
  padding: 6px 12px;
  background: #F9F9F9;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-conversation-history:hover {
  background: #FFFFFF;
  border-color: #FB6E00;
}

.btn-conversation-history.active {
  background: linear-gradient(30deg, #FFC500 0%, #DC2223 41%, #720096 100%);
  color: #FFFFFF;
  border-color: #FB6E00;
}

.conversation-history-content {
  margin-top: 12px;
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 12px;
  background: #F9F9F9;
}

.conversation-entry {
  margin-bottom: 12px;
  padding: 10px;
  background: #FFFFFF;
  border-radius: 4px;
  border-left: 3px solid rgba(0, 0, 0, 0.1);
}

.conversation-entry-user {
  border-left-color: #FB6E00;
}

.conversation-entry-assistant {
  border-left-color: #231F20;
}

.conversation-entry-tool {
  border-left-color: #FB6E00;
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
  color: #231F20;
  font-weight: 400;
}

.conversation-entry-type {
  padding: 2px 8px;
  background: #F9F9F9;
  border-radius: 4px;
  color: #646265;
  font-size: 10px;
  font-weight: 400;
  text-transform: uppercase;
}

.conversation-entry-body {
  margin-top: 8px;
}

.conversation-entry-content {
  margin: 0;
  padding: 8px;
  background: #F9F9F9;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  color: #231F20;
}

.tool-call-info {
  font-size: 12px;
}

.tool-call-info strong {
  color: #231F20;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
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
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  font-weight: 400;
  resize: none;
  transition: all 0.3s;
  color: #231F20;
  background: #FFFFFF;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.chat-input:focus {
  outline: none;
  border-color: #FB6E00;
  box-shadow: 0 0 0 3px rgba(251, 110, 0, 0.1);
}

.chat-input:disabled {
  background: #F9F9F9;
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
  background: #F9F9F9;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.token-stat {
  font-size: 14px;
  font-weight: 400;
  color: #646265;
}

.token-stat strong {
  color: #231F20;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
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
  background: #FFFFFF;
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
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
  border-color: #FB6E00;
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
  font-family: 'Inter', sans-serif;
  color: #646265;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
  color: #231F20;
  margin-bottom: 8px;
  line-height: 1.2;
}

.stat-description {
  font-size: 13px;
  font-weight: 400;
  color: #646265;
  line-height: 1.4;
}

.stats-empty {
  text-align: center;
  padding: 60px 20px;
  color: #646265;
  font-size: 16px;
  font-weight: 400;
}

.header-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-secondary {
  background: #646265;
  color: #FFFFFF;
}

.btn-secondary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(100, 98, 101, 0.3);
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
  background: #FFFFFF;
  border-color: #FB6E00;
}

.mcp-test-result.error {
  background: #FFFFFF;
  border-color: #DC2223;
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
  font-family: 'Inter', sans-serif;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.mcp-test-result.success .mcp-test-status {
  background: #F9F9F9;
  color: #231F20;
}

.mcp-test-result.error .mcp-test-status {
  background: #F9F9F9;
  color: #DC2223;
}

.mcp-test-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  font-weight: 400;
  color: #231F20;
}

.mcp-test-details p {
  margin: 0;
}

.mcp-test-error {
  color: #DC2223;
  font-size: 14px;
  font-weight: 400;
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
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  margin-bottom: 8px;
}

.mcp-response-details summary:hover {
  text-decoration: underline;
}

.mcp-response-details pre {
  background: #231F20;
  color: #FFFFFF;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
  border: 1px solid rgba(0, 0, 0, 0.1);
  margin-top: 8px;
  font-family: 'Inter', monospace;
}

.schema-display {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.schema-display h4 {
  margin: 0 0 16px 0;
  color: #231F20;
  font-size: 18px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.schema-section {
  margin-bottom: 20px;
}

.schema-section h5 {
  margin: 0 0 12px 0;
  color: #231F20;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.schema-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.schema-tag {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 400;
  font-family: 'Inter', sans-serif;
  border: 1px solid;
}

.node-tag {
  background: #FFFFFF;
  color: #FB6E00;
  border-color: #FB6E00;
}

.rel-tag {
  background: #FFFFFF;
  color: #720096;
  border-color: #720096;
}

.prop-tag {
  background: #FFFFFF;
  color: #FFC500;
  border-color: #FFC500;
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
  color: #231F20;
  font-size: 14px;
  font-weight: 400;
  min-width: 120px;
}

.mcp-response-fallback {
  margin-top: 16px;
}

.countdown-timer {
  background: #F9F9F9;
  border: 2px solid #FB6E00;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
  animation: pulse 2s ease-in-out infinite;
}

.countdown-timer.countdown-finished {
  background: #F9F9F9;
  border-color: #FB6E00;
  animation: none;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(251, 110, 0, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(251, 110, 0, 0);
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
  font-family: 'Inter', sans-serif;
  color: #231F20;
  font-size: 14px;
}

.countdown-value {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
  color: #FB6E00;
  font-variant-numeric: tabular-nums;
}

.countdown-value.countdown-warning {
  color: #DC2223;
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
  border-top: 1px solid #FB6E00;
  color: #DC2223;
  font-weight: 400;
  font-size: 14px;
  text-align: center;
}

.tools-section {
  margin-top: 30px;
  padding-top: 30px;
  border-top: 2px solid rgba(0, 0, 0, 0.08);
}

.tools-section h3 {
  margin-bottom: 20px;
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.tool-card {
  background: #FFFFFF;
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.tool-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #FB6E00;
}

.tool-header {
  margin-bottom: 12px;
}

.tool-name {
  margin: 0;
  color: #231F20;
  font-size: 18px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.tool-description {
  color: #646265;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
  margin-bottom: 16px;
}

.tool-parameters {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.tool-parameters strong {
  color: #231F20;
  font-size: 13px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
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
  font-weight: 400;
  color: #646265;
  line-height: 1.5;
}

.tool-params-list code {
  background: #F9F9F9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Inter', monospace;
  color: #FB6E00;
  font-weight: 600;
  font-size: 12px;
}

.tools-empty {
  text-align: center;
  padding: 60px 20px;
  color: #646265;
  font-size: 16px;
  font-weight: 400;
}

.call-tool-section {
  margin-top: 40px;
  padding-top: 30px;
  border-top: 2px solid rgba(0, 0, 0, 0.08);
}

.call-tool-section h3 {
  margin-bottom: 20px;
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.call-tool-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #F9F9F9;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.select-input {
  width: 100%;
  padding: 12px;
  background: #FFFFFF;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  font-weight: 400;
  color: #231F20;
  cursor: pointer;
  transition: border-color 0.3s;
}

.select-input:focus {
  outline: none;
  border-color: #FB6E00;
}

.select-input:disabled {
  background: #F9F9F9;
  cursor: not-allowed;
}

.tool-arguments {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tool-arguments h4 {
  margin: 0 0 12px 0;
  color: #231F20;
  font-size: 16px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.param-type {
  color: #646265;
  font-size: 12px;
  font-weight: 400;
  font-family: 'Inter', monospace;
}

.required {
  color: #DC2223;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.param-description {
  font-size: 12px;
  font-weight: 400;
  color: #646265;
  margin-bottom: 4px;
  font-style: italic;
}

.input-field {
  width: 100%;
  padding: 10px;
  background: #FFFFFF;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  font-size: 14px;
  font-family: 'Inter', sans-serif;
  font-weight: 400;
  color: #231F20;
  transition: border-color 0.3s;
}

.input-field:focus {
  outline: none;
  border-color: #FB6E00;
}

.input-field:disabled {
  background: #F9F9F9;
  cursor: not-allowed;
}

.no-arguments {
  padding: 16px;
  background: #F9F9F9;
  border: 1px solid #FB6E00;
  border-radius: 6px;
  color: #FB6E00;
  font-size: 14px;
  font-weight: 400;
  text-align: center;
}

.tool-result {
  margin-top: 24px;
  padding: 20px;
  background: #FFFFFF;
  border: 2px solid #FB6E00;
  border-radius: 8px;
}

.tool-result h4 {
  margin: 0 0 16px 0;
  color: #231F20;
  font-size: 18px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.result-info {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.result-info p {
  margin: 8px 0;
  font-size: 14px;
  font-weight: 400;
  color: #231F20;
}

.result-content {
  background: #231F20;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 16px;
}

.result-content pre {
  margin: 0;
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.5;
  font-family: 'Inter', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.retrieval-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 2px solid rgba(0, 0, 0, 0.08);
}

.retrieval-tab-button {
  padding: 12px 24px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  font-size: 15px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  color: #646265;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: -2px;
}

.retrieval-tab-button:hover {
  color: #231F20;
  background: #F9F9F9;
}

.retrieval-tab-button.active {
  color: #FB6E00;
  border-bottom-color: #FB6E00;
}

.retrieval-method-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.method-description {
  background: #FFFFFF;
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
}

.method-description h3 {
  margin: 0 0 16px 0;
  color: #231F20;
  font-size: 20px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
}

.method-description p {
  color: #646265;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.7;
  margin-bottom: 12px;
}

.method-summary {
  color: #646265;
  font-size: 15px;
  font-weight: 400;
  line-height: 1.7;
  margin-bottom: 20px;
}

.query-display {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.query-display strong {
  display: block;
  color: #231F20;
  font-size: 14px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.query-code {
  background: #231F20;
  color: #FFFFFF;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.6;
  font-family: 'Inter', monospace;
  margin: 0;
  border: 1px solid rgba(0, 0, 0, 0.1);
  white-space: pre;
}
</style>

