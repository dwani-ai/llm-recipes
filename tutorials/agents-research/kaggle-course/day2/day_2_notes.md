Day 2 Notes - Agent tools and Interoperability with MCP

Model Context Protocol - https://modelcontextprotocol.io/docs/getting-started/intro

- Types of Tools
    - Function Tools - call external user defined functions
    - Agent Tools - Call another Agent as Tool
    - Built in tools  - tools avialble from a foundation model like Gemini - Computer Use, Search API

- Taxonomy of Agent Tools
    One way of categorizing agent tools is by their primary function, or the various types of interactions they facilitate. Here’s an overview of common types:
    -  Information Retrieval: Allow agents to fetch data from various sources, such as web searches, databases, or unstructured documents.
    - Action / Execution: Allow agents to perform real-world operations: sending emails, posting messages, initiating code execution, or controlling physical devices.
    - System / API Integration: Allow agents to connect with existing software systems and APIs, integrate into enterprise workflows, or interact with third-party services.
    - Human-in-the-Loop: Facilitate collaboration with human users: ask for clarification, seek approval for critical actions, or hand off tasks for human judgment.

- Best Practices : 
    - Documentation is Important
        - Use a clear name
        - Describe all input and output parameters
        - Simplify parameter lists
        - Clarify tool descriptions
        - Add targeted examples
        - Provide default values 
    - Describe actions, not implementations
        - Describe what, not how
        - Dont duplicate instructions
        - Dont dictate workflows
        - DO explain tool interactions
    - Publish tasks, not API calls
    - Make tools as granular as possible
        - Define clear responsibilities
        - Don't create multi-tools
    - Design for concise output
        - Don't return large responses
        - Use external systems
            - Artifact Service - https://google.github.io/adk-docs/artifacts/#artifact-service-baseartifactservice
    - Use validation effectively
        - Provide descriptive error messages
        
- MCP - Model Context Protocol
    - Core Architectural Components: Hosts, Clients, and Servers
    - The Communication Layer: JSON-RPC, Transports, and Message Types
        - Base Protocol - JSON-RPC
        - Message Types
            - Requests
            - Results
            - Errors
            - Notifications
    - Transport Mechanisms
            - stdio 
            - Streamable HTTP 
    - Key Primitives: Tools and others
        - server side -   Tools,Resources and Prompts; 
        - client side - Sampling, Elicitation and Roots.

- Tools
    - Tool definitions must conform to a JSON schema with the following fields:
        - name: Unique identifier for the tool
        - title: [OPTIONAL] human-readable name for display purposes
        - description: Human- (and LLM-) readable description of functionality
        - inputSchema: JSON schema defining expected tool parameters
        - outputSchema: [OPTIONAL]: JSON schema defining output structure
        - annotations: [OPTIONAL]: Properties describing tool behavior
            - destructiveHint:
            - idempotentHint:
            - openWorldHint:
            - readOnlyHint:
            - title:
    - JSON Schema - https://modelcontextprotocol.io/specification/2025-06-18/schema#tool

- Tool Results
    - Unstructured Content
        - The Text type represents unstructured string data; the Audio and Image content types contain base64-encoded image or audio data tagged with the appropriate MIME type
    - Structured Content - outputSchema

- Error Handling
    -  standard JSON-RPC errors for protocol issues such as unknown tools, invalid arguments, or server errors. 
    -  by setting the "isError": true parameter in the result object 

- Server Side Capability
    - Resources are intended to provide contextual data that can be accessed and used by the Host application
    - Prompts, allowing the server to provide reusable prompt examples or templates related to its Tools and Resources.

- Client Side
    - Sampling allows an MCP server to request an LLM completion from the client.
    - Elicitation allows an MCP server to request additional user information from the client.
    - Roots define the boundaries of where servers can operate within the filesystem.

- MCP Registry 
    - which provides both a central source of truth for public MCP servers, and also an OpenAPI specification to standardize MCP server declarations
    - https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/

- Advantages for MCP
    - Dynamically Enhancing Agent Capabilities and Autonomy
        - Dynamic Tool Discovery
        - Standardizing and Structuring Tool Descriptions
        - Expanding LLM Capabilities

    - Architectural Flexibility and Future-Proofing
    - Foundations for Governance and Control
    - 
- Critical Risks and Challenges
    - Performance and Scalability Bottlenecks
        - Context Window Bloat
        - Degraded Reasoning Quality
        - Stateful Protocol Challenges
    - Enterprise Readiness Gaps
        - Authentication and Authorization
        - Identity Management Ambiguity
        - Lack of Native Observability

- Tool Discovery - RAG Approach

- Risks and Mitigations
    - Dynamic Capability Injection
        - Explicit allowlist of MCP tools
        - Mandatory Change Notification
        - Tool and Package Pinning
        - Secure API / Agent Gateway
        - Host MCP servers in a controlled environment
    - Tool Shadowing    
        - Tool descriptions can specify arbitrary triggers (conditions upon which the tool should be chosen by the planner). This can lead to security issues where malicious tools overshadow legitimate tools, leading to potential user data being intercepted or modified by attackers.
            - Prevent Naming Collisions
            - Mutual TLS (mTLS)
            - Deterministic Policy Enforcement
            - Require Human-in-the-Loop (HIL)
            - Restrict Access to Unauthorized MCP Servers
    - Malicious Tool Definitions and Consumed Contents
        - Tool descriptor fields, including their documentation and API signature, can manipulate agent planners into executing rogue actions.
            - Input Validation
            - Output Sanitization
            - Separate System Prompts
            - Strict allowlist validation and sanitization of MCP resources
            - Sanitize Tool Descriptions
    - Sensitive information Leaks
        - MCP tools should use structured outputs and use annotations on input/output fields
        - Taint Sources/Sinks
    - No support for limiting the scope of access
        - Tool invocation should use audience and Scoped credentials
        - Use principle of least privilege
        - Secrets and credentials should be kept out of the agent context

- Confused Deputy problem
    - The "confused deputy" problem is a classic security vulnerability where a program with privileges (the "deputy") is tricked by another entity with fewer privileges into misusing its authority, performing an action on behalf of the attacker.