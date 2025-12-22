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
