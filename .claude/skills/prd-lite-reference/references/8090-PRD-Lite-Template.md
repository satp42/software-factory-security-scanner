# **8090 Product Requirements Document (PRD) Template for Customer Solutions**

This document establishes the standard structure and content requirements for all Product Requirements Documents at 8090, applicable across all customer engagements. This template ensures consistency across all client engagements while maintaining specific requirements for each implementation. PRDs following this template provide direction to engineering and align customer expectations.

## **Business Problem**

This section must define the current problem. The explanation will entail inefficiencies and limitations in the client's current process. The description must identify pain points experienced by end users and process challenges. The section must quantify the business impact regarding operational costs, process delays, or missed opportunities. Clearly define the specific business problem that the product aims to solve. The business problem must justify the solution by connecting operational issues to business outcomes. This section must conclude with a concise statement of how 8090's solution addresses these challenges.

This section provides an  overview of the business, outlining what the business is currently trying to accomplish and why this effort is important. It should clearly explain the motivation behind the initiative, including the key problems or opportunities driving the need for change. Explain the core friction points, inefficiencies, or blockers the business is experiencing today and why now is the right time to address them.  Identify the affected business unit and connect the initiative to broader organizational goals. It identifies the primary users and stakeholders of the product. 

The section ends with product's purpose and the name the automation initiative. Provide a vision of the product and its intended impact. The business problem provides context for the rest of the document.

## **Current Process**

Building upon the business problem, this section describes how the business currently operates in the specific area of concern. It focuses strictly on the existing workflow, without referencing any future solutions. The goal is to outline the current state of operations as they relate to the identified pain point or opportunity, providing a clear understanding of what the customer is doing today and where that process is falling short.

The current process section must document the existing business process and its workflows with specific procedural steps in visual form through process maps, flowcharts, and/or value stream maps and in narrative form. This section must identify systems currently used by the client and describe how users interact with these systems. The description must specify where process fragmentation occurs and catalog integration gaps between existing platforms. The section must identify data quality issues, manual tracking methods, and reporting limitations within the current state. This section creates the baseline against which the solution will be measured.

This section must identify all user roles affected by the automation systems and document current pain points experienced by each role. User needs must specify requirements, scalability needs, and process visibility requirements. The section must explain the current process, including challenges for customer service representatives, engineers, specialists, and other users. Requirements must quantify why their current way of doing jobs is slow, inefficient, or expensive. The deliverable describes the current process, including workflows, systems, and stakeholders.

## **Product Description**

This section offers a clear explanation of the product that will be built. It should describe how the product will improve the current process, whether by introducing a completely new solution, integrating it into existing systems, replacing components of the current workflow, or other mechanisms. This section should make it clear to the reader how the product addresses the original business problem and seeks to deliver tangible improvements to the current process.

Focus on what the product must do rather than how it will achieve it, allowing flexibility in design and development. The product description should represent the functional requirements, the information architecture, the interaction design, and the visual design of the user experience. The section must define the user interface and user experience approaches for different roles. 

Define the high-level processes or tasks that will be automated. Call out any operational dashboards and reporting that need to be built to give insight into data processing and key business metrics. Describe the user interface's key features and personas. Outline the key components and functionalities of any dashboards.

State what is to be achieved by the product, no more and no less phrased as actions. Use action-oriented verbs like “Launch,” “Improve,” “Reduce,” or “Increase.” Connect these objectives to the vision of the product. Objectives typically address processing time reduction, accuracy improvement, and operational efficiency. Objectives provide clarity to the team on prioritizing their efforts. Objectives are measured by key results. Key Results provide a clear, measurable way to determine whether an objective has been met, leaving no room for ambiguity or subjective interpretation. They must be specific, time-bound, and verifiable—either achieved or not achieved.

## **Product Features**

Here, the document provides a detailed breakdown of the product's functionality. Each core capability or user-facing feature is described clearly to define the scope and ensure a shared understanding of what the product will do. This section serves as a functional specification that outlines the product's exact capabilities and behaviors.

Provide a clear and descriptive name for each feature. Describe the functionality and purpose of each feature in detail. Outline any specific technical requirements or constraints for each feature. Each feature must be defined with clear boundaries and an implementation approach. Features must address specific limitations identified in the current process section and achieve the product's objectives. The section must specify how multiple features work together to create a complete solution. This section provides a detailed blueprint for implementation.

This section must document the reworked business process with process maps, value stream maps, and service blueprints. Value stream maps must identify where efficiency gains occur in the new process. This section describes the target state that guides implementation decisions. Describe the rules and logic governing the process's workflows. Outline how the automated system will handle exceptions, errors, and human-in-the-loop checks. 

Selective high-fidelity mockups showing UI designs and interactions should be added here. Capture user journeys that map the user's experience through the reimagined process, with epics and user stories that define the product's requirements. 

## **Technical Requirements**

This section covers the product's technical constraints and dependencies. This includes any integration requirements with existing systems or third-party services, as well as compliance or regulatory considerations that must be met. It also outlines scalability, performance, reliability, security, and usability expectations. Any specific technical limitations or architectural requirements should be clearly stated to inform implementation and planning.

This section must define external system dependencies, including integration patterns with client systems. The section must specify whether integrations are read-only, write-only, or bi-directional, with justification for each approach. The scope must include data validation methods, error handling procedures, and integration unavailability scenarios. This section establishes technical boundaries for the development team. Identify any external and internal systems the product needs to integrate (e.g., Brightree, Epic, Oracle DB, SAP, etc.). Describe any API integrations that are required. 

This section must document data fields, validation rules, and system behaviors for document processing systems. Requirements must include field definitions with data types, validation rules, and default values. The section must specify behavior for edge cases and integration failures. 

Requirements must be organized in a structured format and traceable to product features. This section provides technical specifications for the development team.

## **Measurement**  

This section defines how the product's performance will be measured in relation to the business problem. These metrics will differ from the key results defined in the business problem section as they will be more granular and specific to the software. All measurements must be derived explicitly from the software's capabilities and behaviors. Measurements of metrics outside of the software's control should not be included.

Define specific acceptance conditions that must be met for the software to be deployed to production.

The evaluation plan outlines a methodology for assessing whether the product is "working.” Use this section to define quality metrics and gates. Metrics must include quantity, quality, and tracking method. The data collection part details what metrics will be tracked, the collection process, the frequency of data gathering, and the client's responsibilities to enable feedback collection. Additionally, it explains how spot checks are conducted and recorded into a systematic category of prioritized issues. 

Additionally, when LLMs are part of the solution, it is important to estimate the inference cost. Strategies for optimizing inference cost should be explored. Regular monitoring and analysis of inference costs should be performed. The PRD should include cost, latency, and accuracy tradeoffs for model selection. 

## **Appendix**

The appendix must define key terms and acronyms used throughout the documentation. Most pictures, diagrams, and tables should be in the appendix so all stakeholders can read the main doc. Supporting documents and references must be included to provide additional context. This section ensures a common understanding of terminology across teams. The reference materials may consist of technical specifications and market research. The stakeholders sub-section identifies key individuals involved in the project, their roles, and their responsibilities.

***

## **Authoring Guidelines** 

### **Context**

Each PRD is fully fleshed out. No bullets. Always use narrative style full-formed statements. No speculation. A PRD will ship in its entirety, so the scope is dialed in and fully fleshed out for Engineering and Design to take it and build and execute against the specifications of a collaboration effort between Engineering  Product and Design. Every time the PRD is approved, it is frozen. Any changes to the PRD will result in a new version of the PRD, and the PRD evolves, and so does the solution incrementally. Do not change all the content; just add the extras. The narrative style should include more about the workflow, making it as granular as possible, not just keep it open-ended or vague. When Engineers and Designers read this, they should understand what needs to be built and have no questions about the product. This is the PRD; it is the entirety of what needs to be built. 

### **Rules To Be Followed**

You must always use clear and plain English. Never use fluffy language; simply state what the software does exactly as it happens—clarity matters above everything else. Stick to the facts. You should not hide behind a bunch of bullet points and corporate jargon. Instead, write in narrative form to encourage connectivity in the documentation. Use active language.

Be specific and state all technical or business state constraints and non-negotiables. Write precise user stories or feature descriptions in concise language. Make sure each story is isolated and clearly stated. Add explicit acceptance criteria for each issue, epic, bug, or user story. These criteria define done-definition and edge cases. Describe all critical business logic rules or formulas in plain language.

Maintain a consistent format for similar items. If you list user stories as User Story 1 or User Story 2, do the same throughout. If acceptance criteria are bullet points starting with a verb, keep that style. Use simple language and define all acronyms at least once, like academic papers. Avoid ambiguous wording and weasel words. Use adverbs sparingly and adjectives only when necessary and substantiated by data.