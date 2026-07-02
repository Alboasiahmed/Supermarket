// Same-origin path: CloudFront routes "/chat" to the backend, everything else to S3.
// (For local testing, temporarily change this back to "http://localhost:8000/chat".)
const API_URL = "/chat";

function addMessage(text, who) {
  const messages = document.getElementById("expert-messages");
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

async function sendExpert(text) {
  text = (text || "").trim();
  if (!text) return;

  const input = document.getElementById("expert-text");
  addMessage(text, "user");
  input.value = "";

  const typing = addMessage("…", "bot");   // placeholder while we wait

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    typing.textContent = data.reply;
  } catch (e) {
    typing.textContent = "Sorry, I can't reach the store assistant right now.";
  }
}