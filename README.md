# Anonymous Research Artifact

This repository contains the implementation and deployment artifacts
associated with the submitted paper.

It consists of two main components:

- `fl-thesis/`: the Flower application and deployment/orchestration
  scripts used for the experiments.
- `fl-middleware/`: the resource discovery, matching, and allocation
  middleware described in the paper.

## Testbed access

Running the deployment scripts requires valid user accounts and
authorization for the corresponding research infrastructures,
including Grid'5000, Chameleon, and FIT IoT-LAB.

For security and double-blind review, this repository does not
contain user credentials, passwords, API secrets, SSH private keys,
or testbed-specific personal identifiers. Users wishing to reproduce
the deployments must provide their own credentials and account
information.

Some scripts therefore require environment variables or local
configuration values before execution. Example configuration files
and setup instructions are provided where applicable.

## Reproducibility

The repository contains the source code, middleware implementation,
provider-specific deployment scripts, and experiment configuration
used in the paper. Access to the physical testbeds remains subject
to resource availability and to the authentication and authorization
policies of each infrastructure.

##  Code Files
FL Application       →    fl-thesis/
Deployment scripts   →    fl-thesis/scripts/
Middleware            →    fl-middleware/
Provider adapters     →    fl-middleware/app/...
REST API              →    fl-middleware/app/api/...