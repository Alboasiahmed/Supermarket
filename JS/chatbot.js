const BACKEND_URL = 'http://localhost:8000/chat';  // change to your server when live

async function sendExpert(text) {
  if (!text.trim()) return;
  const messages = document.getElementById('expert-messages');
  document.getElementById('expert-text').value = '';

  // show the user's message
  messages.innerHTML += '<div class="msg user">' + text + '</div>';
  messages.scrollTop = messages.scrollHeight;

  try {
    const res = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    messages.innerHTML += '<div class="msg bot">' + data.response + '</div>';
  } catch {
    messages.innerHTML += '<div class="msg bot">(Demo mode — connect your backend to get real answers)</div>';
  }
  messages.scrollTop = messages.scrollHeight;
}