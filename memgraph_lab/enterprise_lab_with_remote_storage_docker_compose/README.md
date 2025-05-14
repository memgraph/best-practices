# Memgraph Lab Enterprise Edition with remote storage deployment in Docker compose

This example demonstrates how to deploy Memgraph Enterprise with Memgraph Lab and remote storage 
in a docker compose file. The remote storage will save in this case everything related to features
such as query sharing inside the same Memgraph instance. If you wish to have remote storage separated,
you can check the guide on [enabling Enterprise Lab with separate remote storage](../enterprise_lab_with_separate_remote_storage_docker_compose/).

## 🚀 How to Run Memgraph with Docker

2. To run Memgraph and Memgraph Lab, simply do the following command:

```bash
docker compose up
```


## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph MAGE v3.2.0**
- **Memgraph Lab v3.2.0**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!


## 🏢 Enterprise or Community?

> 🛑 This example uses **Memgraph Enterprise Edition** and **Memgraph Lab Enterprise Edition**.
