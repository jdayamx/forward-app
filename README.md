
# Socat Forwarding API

This API allows you to create temporary TCP proxies using `socat`. It provides endpoints to open, close, and list port forwarding connections dynamically.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Response Codes](#response-codes)
- [Notes](#notes)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/socat-forwarding-api.git
    cd socat-forwarding-api
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3. Make sure `socat` is installed on your system. You can install it using:

    - **Debian/Ubuntu:**
        ```bash
        sudo apt-get install socat
        ```

    - **CentOS/RHEL:**
        ```bash
        sudo yum install socat
        ```

4. Run the Flask app:

    ```bash
    python server.py
    ```

The application will run on `http://0.0.0.0:3003`.

## Usage

Once the app is running, you can interact with the API through the following endpoints.

### API Endpoints

#### `GET /open?port=PORT`

This endpoint creates a proxy forwarding from `<PORT + 1>` to `<PORT>`.

**Example Request:**

```bash
GET /open?port=8080
```

**Example Response:**

```json
{
  "status": "success",
  "local_port": 8080,
  "public_port": 8081
}
```

**If the port is already forwarded:**

```json
{
  "status": "error",
  "message": "Port 8080 already forwarded to 8081"
}
```

#### `GET /close?port=PORT`

This endpoint closes the forwarding from `<PORT + 1>` to `<PORT>`.

**Example Request:**

```bash
GET /close?port=8080
```

**Example Response:**

```json
{
  "status": "success",
  "message": "Forward 8080 to 8081 is closed"
}
```

**If the port is not forwarded:**

```json
{
  "status": "error",
  "message": "Port already closed"
}
```

#### `GET /list`

This endpoint lists all active port forwarding connections.

**Example Request:**

```bash
GET /list
```

**Example Response:**

```json
[
  {
    "local_port": 8080,
    "public_port": 8081,
    "pid": 12345
  },
  {
    "local_port": 3000,
    "public_port": 3001,
    "pid": 12346
  }
]
```

## Response Codes

- `200 OK`: The request was successful.
- `400 Bad Request`: The request was malformed or the port is already forwarded/closed.

## Notes

- All requests to the API are `GET` requests.
- `local_port`: The internal port to which the traffic is forwarded.
- `public_port`: The open port for external connections.
- After restarting the Flask app, previously created forwarding rules will be lost, and you will need to recreate them.
