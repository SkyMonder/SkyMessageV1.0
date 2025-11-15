const socket = io();
let localStream, pc;
let currentCall = null;
let username = null;
let chatWith = null;

const authDiv = document.getElementById('auth');
const mainDiv = document.getElementById('main');

document.getElementById('btn-register').onclick = async () => {
    const res = await fetch('/api/register', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            username: document.getElementById('reg-username').value,
            password: document.getElementById('reg-password').value
        })
    });
    alert((await res.json()).msg);
};

document.getElementById('btn-login').onclick = async () => {
    const res = await fetch('/api/login', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            username: document.getElementById('login-username').value,
            password: document.getElementById('login-password').value
        })
    });
    const data = await res.json();
    if(data.access_token){
        username = document.getElementById('login-username').value;
        localStorage.setItem('token', data.access_token);
        authDiv.style.display='none';
        mainDiv.style.display='block';
        socket.emit('join', {username});
    } else alert(data.msg);
};

// ===== SEARCH USERS =====
const searchInput = document.getElementById('search');
const searchResults = document.getElementById('search-results');
searchInput.oninput = async () => {
    const q = searchInput.value;
    if(!q) return searchResults.innerHTML='';
    const token = localStorage.getItem('token');
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`, {
        headers:{'Authorization':'Bearer '+token}
    });
    const users = await res.json();
    searchResults.innerHTML='';
    users.forEach(u=>{
        const li = document.createElement('li');
        li.textContent=u;
        li.onclick=()=>loadChat(u);
        searchResults.appendChild(li);
    });
};

// ===== CHAT =====
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
document.getElementById('send-chat').onclick = async () => {
    const msg = chatInput.value;
    if(!msg || !chatWith) return;
    socket.emit('chat_message',{user:username,to:chatWith,msg});
    chatInput.value='';
};

function loadChat(user){
    chatWith = user;
    document.getElementById('chat-with').textContent=user;
    chatMessages.innerHTML='';
    const token = localStorage.getItem('token');
    fetch(`/api/messages/${user}`,{headers:{'Authorization':'Bearer '+token}})
    .then(res=>res.json())
    .then(msgs=>{
        msgs.forEach(m=>{
            const div = document.createElement('div');
            div.textContent = m.sender+': '+m.text;
            chatMessages.appendChild(div);
        });
    });
}

// ===== SOCKET EVENTS =====
socket.on('chat_message',data=>{
    if(data.user===chatWith || data.user===username){
        const div = document.createElement('div');
        div.textContent = data.user+': '+data.msg;
        chatMessages.appendChild(div);
    }
});

socket.on('incoming_call', data=>{
    currentCall = data.caller;
    document.getElementById('call-with').textContent=currentCall;
    document.getElementById('call-container').style.display='block';
});

socket.on('call_response', data=>{
    if(data.response==='decline' || data.response==='end'){
        endCall();
        alert('Вызов завершён');
    }
});

// ===== CALL BUTTONS =====
document.getElementById('call-btn').onclick=()=>startCall(chatWith);
document.getElementById('btn-answer').onclick=()=>answerCall();
document.getElementById('btn-decline').onclick=()=>declineCall();
document.getElementById('btn-end').onclick=()=>endCall();
document.getElementById('btn-mic').onclick=()=>toggleMic();
document.getElementById('btn-camera').onclick=()=>toggleCam();

async function startCall(target){
    if(!target) return alert('Выберите пользователя');
    pc = new RTCPeerConnection();
    localStream = await navigator.mediaDevices.getUserMedia({video:true,audio:true});
    document.getElementById('localVideo').srcObject = localStream;
    localStream.getTracks().forEach(track => pc.addTrack(track,localStream));
    pc.ontrack = e=>document.getElementById('remoteVideo').srcObject=e.streams[0];
    pc.onicecandidate = e=>{
        if(e.candidate) socket.emit('webrtc_signal',{target,signal:e.candidate,from:username});
    };
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    socket.emit('call_user',{caller:username,target});
    socket.emit('webrtc_signal',{target,signal:offer,from:username});
}

async function answerCall(){
    if(!currentCall) return;
    pc = new RTCPeerConnection();
    localStream = await navigator.mediaDevices.getUserMedia({video:true,audio:true});
    document.getElementById('localVideo').srcObject = localStream;
    localStream.getTracks().forEach(track => pc.addTrack(track,localStream));
    pc.ontrack = e=>document.getElementById('remoteVideo').srcObject=e.streams[0];
    pc.onicecandidate = e=>{
        if(e.candidate) socket.emit('webrtc_signal',{target:currentCall,signal:e.candidate,from:username});
    };
    document.getElementById('call-container').style.display='block';
}

function declineCall(){
    if(currentCall) socket.emit('call_response',{caller:currentCall,response:'decline'});
    currentCall=null;
    document.getElementById('call-container').style.display='none';
}

function endCall(){
    if(pc) pc.close();
    pc=null;
    currentCall=null;
    document.getElementById('call-container').style.display='none';
}

function toggleMic(){
    if(localStream) localStream.getAudioTracks()[0].enabled=!localStream.getAudioTracks()[0].enabled;
}

function toggleCam(){
    if(localStream) localStream.getVideoTracks()[0].enabled=!localStream.getVideoTracks()[0].enabled;
}

// ===== SIGNAL =====
socket.on('webrtc_signal', async data=>{
    if(!pc){
        pc = new RTCPeerConnection();
        localStream = await navigator.mediaDevices.getUserMedia({video:true,audio:true});
        document.getElementById('localVideo').srcObject=localStream;
        localStream.getTracks().forEach(track=>pc.addTrack(track,localStream));
        pc.ontrack=e=>document.getElementById('remoteVideo').srcObject=e.streams[0];
        pc.onicecandidate=e=>{
            if(e.candidate) socket.emit('webrtc_signal',{target:data.from,signal:e.candidate,from:username});
        };
    }

    if(data.signal.type==='offer'){
        await pc.setRemoteDescription(new RTCSessionDescription(data.signal));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        socket.emit('webrtc_signal',{target:data.from,signal:answer,from:username});
        currentCall=data.from;
        document.getElementById('call-with').textContent=currentCall;
        document.getElementById('call-container').style.display='block';
    } else if(data.signal.type==='answer'){
        await pc.setRemoteDescription(new RTCSessionDescription(data.signal));
    } else if(data.signal.candidate){
        await pc.addIceCandidate(new RTCIceCandidate(data.signal));
    }
});
