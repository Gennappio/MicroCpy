# OpenCellComms: Constraining AI Coding Agents for Readable, Observable ABM Models

## Working thesis

OpenCellComms is a software environment for building agent-based models (ABMs) in
biology. Its central contribution is not only that it runs simulations, and not only
that it has a graphical interface. Its contribution is that it gives biologists and
coding agents a shared, constrained representation of a model.

Biologists often understand the biological mechanism they want to test, but they
cannot always write and maintain complex simulation code. Coding agents make code
generation easier, but they do not remove the barrier. They can generate a large
amount of code quickly, and that code can overwhelm both programmers and biologists.
They also infer missing architecture instead of asking. The result can be code that
runs but is difficult to understand, modify, validate, interrogate, or share.

OpenCellComms addresses this by constraining the coding agent. It provides a
node-based GUI, a workflow intermediate representation, a one-file-one-node code
organization, plugin and workflow conventions, semantic validators, a minimal ABM
library, and AI authoring protocols. The goal is to move from a theoretical
biological model to functioning ABM code with the fewest correction iterations.

## Article outline

1. Introduction and motivation
2. Design principles
3. Software organization
4. Workflow intermediate representation
5. Static semantic validation
6. Minimal ABM library
7. AI-guided code generation
8. Observation, validation, and sharing
9. Use-case chapter skeleton
10. Discussion and limitations
