## init prompt

This is an initialization prompt to setup an agentic workflow to create a website. The complete agentic workflow must be setup in .claude together with 1 @CLAUDE.md pointing to the relevant context in .claude. The agentic workflow contains the following roles:
- **orchestrator** plans the design of the website and keeps track of the status of each part of the website (frondend, backend, design astethics). The orchestrator does not write code itself. It only reports tasks to sub-agents. Task list is kept up to date from reports by sub-agents after completion of their task. Individual tasks are planned by the orchestrator with the goal to limit the scope of each individual task as much as possible (create hyper-specific sub-agent goals). The task list is kept seperate between the different parts of the website. After a task has been completed the code related to the task is tested and reviewed by a code reviewer sub-agent.
- **Frond-end coder**: Executes tasks given by the orchestrator on the front-end of the website
- **Back-end coder**: Executes tasks given by the orchestrator on the back-end of the website
- **design coder**: Executes tasks given the orchestrator on the front-end focused on the design part of the website.
- **code reviewer**: Reviews and tests code written by the three coder sub-agents.  The review from the sub-agent is structured in consise constructive bullet points. The review is split in "required", "suggested-major", and "suggested-minor" changes. Required changes must be complted by the coder agent. suggested-major changes need to be passed by the coder agent but can be overruled if the agent thinks it is part of a different future task (saved in backlog) or has argument for the change being not correct. If the review has 0 required changes and 0 suggested-major changes the task is completed. "suggested-minor" changes are backlogged and grouped together for a future task.

Each role has an individual CLAUDE.md file with information on the role. The specific code languages, style, claude skills that each role can/must use need to be in the CLAUDE.md files. Rules on the scope of each role need to be in CLAUDE.md files.

Code languages to use:
- HTML
- CSS
- Python

Other tools to use:
- /wireframes (skill from https://github.com/Magdoub/claude-wireframe-skill/)
- superpowers (plugin superpowers@superpowers-marketplace)
- frontend-design (plugin frontend-design@claude-plugins-official)

## Comments
The developer has in general limited knowledge on website development. Create enough context for each coder based on common practices and relevant tools for that coder agent. Poll the user on general concept and design of the website. The internal implementation strategy should be handled by the agentic workflow

## Best Practices from developer
 Best practices from my perspective are a combination of things people have said here along with some additional stuff.

    Absolutely install Superpowers. Gamechanger all the way:
    /plugin marketplace add obra/superpowers-marketplace
    /plugin install superpowers@superpowers-marketplace

    Install the official frontend-design plugin:
    /plugin install frontend-design@claude-plugins-official

    Read this:
    https://github.com/anthropics/claude-cookbooks/blob/main/coding/prompting_for_frontend_aesthetics.ipynb

    Using the knowledge from above, use an AI tool to generate /wireframes/. Not mockups, not pages, just wirefames. There's tools like https://bareminimum.design/ or even Gemini is pretty good. Wireframes are MUCH easier to describe changes you want and have a proper result be presented.

    Using all of the above, invoke the /superpowers:brainstorm tool. Feed it the detailed prompt you built using the document from #3 and the wireframes you generated using #4. Answer its clarifying questions. It will create a design plan.

    Invoke the /frontend-design:frontend-design tool and feed it the design plan created in #5 and the wireframe from #4

## website concept

### Broad concept

The website is learning tool for High-school students to learn about Particle Physics trough Future Collider Experiments. The website is intended as a game to search for new physics trough data analysis. A Python only based version of the website of which the concept mist be based can be found here (https://github.com/kskovpen/fce).

# Style concept
The style of the website follows a simplistic and sober style. Limit bright colors in general except for special highlighted features. The website should feel like a tutorial / game on Particle Physics analysis so include a game-like design in the front-end

### Python for data processing
The processing of data must still be done in python and follow the same strategy as in https://github.com/kskovpen/fce.

### Frond-end
The front-end design can be significantly re-designed compared to the Python-only version. The esthetics of the Python-only version were limited by the packages available. The website frond-end must include the following things that are not currently in the design:
- Progression of the user troughout the tutorial / game
- More dynamic toolbars and menus compared to the previous version


### Back-end
The developer has limited back-end knowledge for website design. Create a back-end design based on common uses that works together with the data processing with python.
