# Memgraph core dump generation with Docker Compose

This example demonstrates how to run Memgraph in a Docker container configured to generate core dumps, which can be useful for debugging and diagnosing crashes.

## ⚙️ How to Enable Core Dump Generation

1. Mount a persistent volume where core dumps will be saved (e.g., `/tmp/cores`).
2. Ensure the host system allows writing core dumps to that path:
   ```bash
   chmod a+rwx /tmp/cores
   echo "/tmp/cores/core.%e.%p.%h.%t" | sudo tee /proc/sys/kernel/core_pattern
````

3. Use the provided script to trigger a segmentation fault inside the container.

## 🚀 How to Run the Example

1. Make the script executable:

   ```bash
   chmod +x generate_core_dump.sh
   ```

2. Start the Memgraph container (make sure `docker-compose.yml` is properly configured).

3. Run the crash script:

   ```bash
   ./generate_core_dump.sh
   ```

4. Check the `/tmp/cores` directory for a core dump file:

   ```bash
   ls -lh /tmp/cores
   ```

## 🔖 Version Compatibility

This example was built and tested with:

* **Memgraph RelWithDebInfo Docker image 3.2.1**
* **Ubuntu 24.04**

## 🧠 What This Example Includes

* A `docker-compose.yml` configured with the necessary capabilities (`privileged: true`)
* A crash simulation script that:

  * Installs `gcc` inside the container
  * Compiles and runs a simple program that forces a `SIGSEGV`
  * Triggers a core dump if the container is correctly configured

## 🧪 Note on Debugging

The core dump can be analyzed with `gdb`:

```bash
gdb /usr/lib/memgraph/memgraph /tmp/cores/core.memgraph.XXXX
```

Make sure to use the **RelWithDebInfo** image of Memgraph to include debug symbols.

## 🏢 Enterprise or Community?

This example works with **Memgraph Community Edition** as long as RelWithDebInfo image is provided

## 🤝 Need Help?

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help! 