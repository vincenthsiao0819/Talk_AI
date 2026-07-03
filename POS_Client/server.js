const http = require('http');
const url = require('url');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

process.on('uncaughtException', (err) => {
    console.error('Caught exception:', err);
});
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

let MsEdgeTTS, OUTPUT_FORMAT;
try {
    const msedge = require('msedge-tts');
    MsEdgeTTS = msedge.MsEdgeTTS;
    OUTPUT_FORMAT = msedge.OUTPUT_FORMAT;
} catch (e) {
    console.error("Failed to load msedge-tts module:", e);
}

const lastWelcomeTimes = new Map();
let pendingNames = new Set();
let batchTimer = null;
const BATCH_WINDOW_MS = 500; // 0.5 second batch window
const DEBOUNCE_MS = 300000; // 5 minutes debounce per person

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    
    if (parsedUrl.pathname === '/welcome' || parsedUrl.pathname === '/speak') {
        let text = "家人";
        if (req.method === 'GET') {
            text = parsedUrl.query.name || parsedUrl.query.text || "家人";
            handleRequest(text, res, parsedUrl.pathname === '/welcome');
        } else if (req.method === 'POST') {
            let body = '';
            req.on('data', chunk => { body += chunk.toString(); });
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    let text = data.name || data.text || "家人";
                    let userText = data.userText || null;
                    handleRequest(text, res, parsedUrl.pathname === '/welcome', userText);
                } catch(e) {}
            });
        }
    } else {
        res.writeHead(404);
        res.end();
    }
});

function handleRequest(text, res, isWelcome, userText = null) {
    let safeText = text.replace(/['"`$]/g, "").replace(/\(.*?\)/g, "").trim();
    
    if (isWelcome) {
        console.log(`\n[${new Date().toISOString()}] [HA Request] 收到開門推播請求: ${safeText}`);
        const now = Date.now();
        const incomingNames = safeText.split(/[\s、]+/);
        const newNames = [];
        
        for (const name of incomingNames) {
            if (!name) continue;
            const lastTime = lastWelcomeTimes.get(name) || 0;
            if (now - lastTime >= DEBOUNCE_MS) {
                newNames.push(name);
                lastWelcomeTimes.set(name, now);
            }
        }
        
        if (newNames.length === 0) {
            console.log(`[${new Date().toISOString()}] [Debounce] 忽略重複請求 (5分鐘防呆): ${safeText}`);
            res.writeHead(200);
            res.end(JSON.stringify({status: "ignored", message: "debounced"}));
            return;
        }
        
        for (const name of newNames) {
            pendingNames.add(name);
        }
        
        res.writeHead(200);
        res.end(JSON.stringify({status: "queued", text: newNames.join("、")}));

        if (!batchTimer) {
            console.log(`[${new Date().toISOString()}] [Batching] 開啟 500ms 收集視窗...`);
            batchTimer = setTimeout(() => {
                const namesArray = Array.from(pendingNames);
                pendingNames.clear();
                batchTimer = null;
                
                const combinedNames = namesArray.join("、");
                console.log(`[${new Date().toISOString()}] [Batching] 收集完成，最終廣播名單: ${combinedNames}`);
                executeSpeak(combinedNames, true, null);
            }, BATCH_WINDOW_MS);
        }
    } else {
        // Direct speak (for Chat/AI)
        console.log(`\n[${new Date().toISOString()}] [Chat Request] 收到直接播報請求: ${safeText}`);
        executeSpeak(safeText, false, userText);
        res.writeHead(200);
        res.end(JSON.stringify({status: "success", text: safeText}));
    }
}

async function executeSpeak(safeText, isWelcome, userText) {
    try {
        if (!MsEdgeTTS) throw new Error("TTS Module not loaded");
        
        const tts = new MsEdgeTTS();
        await tts.getVoices(); 
        await tts.setMetadata("zh-TW-HsiaoChenNeural", OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);
        
        let textToSpeak = safeText;
        if (isWelcome) {
            let greetingBase64 = "5q2h6L+O5Zue5a62"; // "歡迎回家"
            let greeting = Buffer.from(greetingBase64, 'base64').toString('utf8');
            textToSpeak = safeText + "，" + greeting; // 用逗號停頓會比較自然
        }
        
        console.log(`[${new Date().toISOString()}] [TTS] 開始向微軟產生 MP3 語音...`);
        const { audioStream } = tts.toStream(textToSpeak);
        
        const chunks = [];
        audioStream.on('data', chunk => chunks.push(chunk));
        audioStream.on('close', () => {
            const timestamp = Date.now();
            const audioFile = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\current_welcome_" + timestamp + ".mp3";
            fs.writeFileSync(audioFile, Buffer.concat(chunks));
            console.log(`[${new Date().toISOString()}] [TTS] 語音檔案產生完畢: ${audioFile}`);
            
            let displayText = isWelcome ? safeText : textToSpeak;
            if (!isWelcome && userText) {
                displayText = "🗣️ You: " + userText + "\n\n🦞 Lobster: " + textToSpeak;
            }
            triggerPopup(isWelcome, displayText, audioFile);
            
            setTimeout(() => {
                try {
                    if (fs.existsSync(audioFile)) {
                        fs.unlinkSync(audioFile);
                        console.log(`[${new Date().toISOString()}] [Cleanup] 已刪除過期語音檔: ${audioFile}`);
                    }
                } catch(e) {}
            }, 60000);
        });
        audioStream.on('error', (err) => {
            console.error(`[${new Date().toISOString()}] [TTS Error] 串流失敗:`, err);
        });
    } catch(err) {
        console.error(`[${new Date().toISOString()}] [Edge TTS Error] 模組初始化失敗:`, err);
    }
}

function triggerPopup(isWelcome, text, audioFile) {
    // UTF-8 to Base64 protection
    let b64Text = Buffer.from(text, 'utf8').toString('base64');
    
    // NEW: Use C# FastWelcome.exe instead of PowerShell
    let exePath = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\FastWelcome.exe";
    let cmd = `"${exePath}" "${b64Text}" "${audioFile}"`;
    
    // IF not welcome, maybe we still use Welcome_Chat.ps1 for Chat layout, or adapt FastWelcome
    if (!isWelcome) {
        let scriptPath = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\Welcome_Chat.ps1";
        cmd = `powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "${scriptPath}" -Base64Text "${b64Text}" -AudioFile "${audioFile}"`;
    }
    
    console.log(`[${new Date().toISOString()}] [Launch] 觸發 UI 顯示與播放: ${cmd}`);
    
    const child = exec(cmd, (error, stdout, stderr) => {
        if (error) {
            console.error(`[${new Date().toISOString()}] [Crash] FastWelcome 異常結束 (Exit Code: ${error.code})`);
            console.error(stderr);
            return;
        }
        console.log(`[${new Date().toISOString()}] [Finish] FastWelcome 正常結束 (Exit Code: 0)`);
    });
    
    // Listen to stdout from FastWelcome.exe
    child.stdout.on('data', (data) => {
        const lines = data.toString().split('\n');
        lines.forEach(line => {
            if (line.trim()) console.log(`[FastWelcome] ${line.trim()}`);
        });
    });
}

// Cleanup old files on startup
try {
    const dir = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\";
    const files = fs.readdirSync(dir);
    for (const file of files) {
        if (file.startsWith("current_welcome_") && file.endsWith(".mp3")) {
            try { fs.unlinkSync(path.join(dir, file)); } catch(e) {}
        }
    }
} catch(e) {}

server.listen(8081, '0.0.0.0', () => {
    console.log(`[${new Date().toISOString()}] [System] FastWelcome API (v2) listening on port 8081. Powered by EdgeTTS & C# Native Executable.`);
});
