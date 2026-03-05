import { io } from "socket.io-client";

const socket = io("/", {
  path: "/ws/socket.io",
  autoConnect: false,
  auth: () => {
    const token = localStorage.getItem("access_token");
    return { token };
  },
});

export default socket;
