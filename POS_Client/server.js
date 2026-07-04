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

const pendingNames = new Set();
let batchTimer = null;
const BATCH_WINDOW_MS = 500; 

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    let pathname = parsedUrl.pathname;
    let queryText = parsedUrl.query.text;

    if (req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk.toString());
        req.on('end', () => {
            if (pathname === '/speak' || pathname === '/welcome') {
                handleRequest(pathname === '/welcome', body.trim(), res, parsedUrl.query.user_text);
            } else {
                res.writeHead(404);
                res.end('Not Found');
            }
        });
    } else if (req.method === 'GET') {
        if (pathname === '/speak' || pathname === '/welcome') {
            handleRequest(pathname === '/welcome', queryText || "", res, parsedUrl.query.user_text);
        } else if (pathname === '/') {
            res.writeHead(404);
            res.end();
        } else {
            res.writeHead(404);
            res.end('Not Found');
        }
    }
});

function handleRequest(isWelcome, text, res, userText) {
    if (!text) {
        res.writeHead(400);
        res.end(JSON.stringify({status: "error", message: "text required"}));
        return;
    }

    let safeText = text.replace(/"/g, '\\"');
    
    if (isWelcome) {
        console.log(`\n[${new Date().toISOString()}] [HA Request] 收到歡迎廣播請求: ${safeText}`);
        const now = Date.now();
        const incomingNames = safeText.split(/[、\s和,]+/);
        
        let newNames = [];
        for (const name of incomingNames) {
            if (!name) continue;
            // Ignore completely duplicate broadcasts within 5 seconds (debouncing)
            let cachePath = path.join("C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\", `debounce_${Buffer.from(name).toString('hex')}.tmp`);
            try {
                if (fs.existsSync(cachePath)) {
                    let stats = fs.statSync(cachePath);
                    if (now - stats.mtimeMs < 5000) {
                        console.log(`[${new Date().toISOString()}] [Debounce] 忽略重複請求 (5秒內): ${name}`);
                        continue;
                    }
                }
                fs.writeFileSync(cachePath, now.toString());
            } catch(e) {}
            
            newNames.push(name);
            pendingNames.add(name);
        }
        
        if (newNames.length === 0) {
            res.writeHead(200);
            res.end(JSON.stringify({status: "ignored", message: "debounced"}));
            return;
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
                console.log(`[${new Date().toISOString()}] [Batching] 收集完成，最終名單: ${combinedNames}`);
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
        let displayText = safeText;
        
        if (isWelcome) {
            // Process names: ensuring "親愛的" is always at the end
            let names = safeText.split(/[、\s和,]+/);
            let dearIndex = names.indexOf("親愛的");
            if (dearIndex !== -1) {
                names.splice(dearIndex, 1); // Remove from current position
                names.push("親愛的");       // Put it at the very end
            }
            names = names.filter(n => n.trim() !== "");
            let formattedNames = names.join("、");
            
            let greetingBase64 = "5q2h6L+O5Zue5a62"; // "歡迎回家"
            let greeting = Buffer.from(greetingBase64, 'base64').toString('utf8');
            
            textToSpeak = formattedNames + "，" + greeting; 
            displayText = formattedNames + "... " + greeting;
        } else {
            if (userText) {
                displayText = "🗣️ You: " + userText + "\n\n🦞 Lobster: " + textToSpeak;
            }
        }
        
        console.log(`[${new Date().toISOString()}] [TTS] 開始產生 MP3 語音... (語音內容: ${textToSpeak})`);
        const { audioStream } = tts.toStream(textToSpeak);
        
        const chunks = [];
        audioStream.on('data', chunk => chunks.push(chunk));
        audioStream.on('close', () => {
            const timestamp = Date.now();
            const audioFile = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\current_welcome_" + timestamp + ".mp3";
            fs.writeFileSync(audioFile, Buffer.concat(chunks));
            console.log(`[${new Date().toISOString()}] [TTS] 語音檔案產生完畢: ${audioFile}`);
            
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
    let b64Text = Buffer.from(text, 'utf8').toString('base64');
    let cmd = "";

    if (isWelcome) {
        // Use C# FastWelcome.exe for absolute instant UI speed + newly restored WMPlayer COM support for audio
        let exePath = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\FastWelcome.exe";
        cmd = `"${exePath}" "${b64Text}" "${audioFile}"`;
    } else {
        // Fallback for Chat UI if needed
        let scriptPath = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\Welcome_Chat.ps1";
        cmd = `powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "${scriptPath}" -Base64Text "${b64Text}" -AudioFile "${audioFile}"`;
    }
    
    console.log(`[${new Date().toISOString()}] [Launch] 觸發 UI 顯示與播放: ${cmd}`);
    
    const child = exec(cmd, (error, stdout, stderr) => {
        if (error) {
            console.error(`[${new Date().toISOString()}] [Crash] UI 程式異常結束 (Exit Code: ${error.code})`);
            console.error(stderr);
            return;
        }
        console.log(`[${new Date().toISOString()}] [Finish] UI 程式正常結束 (Exit Code: 0)`);
    });

    if (isWelcome) {
        child.stdout.on('data', (data) => {
            const lines = data.toString().split('\n');
            lines.forEach(line => {
                if (line.trim()) console.log(`[FastWelcome] ${line.trim()}`);
            });
        });
    }
}

// Cleanup old files on startup
try {
    const dir = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\";
    const files = fs.readdirSync(dir);
    for (const file of files) {
        if (file.startsWith("current_welcome_") && file.endsWith(".mp3")) {
            fs.unlinkSync(path.join(dir, file));
        }
    }
} catch(e) {}

server.listen(8081, () => {
    console.log(`[${new Date().toISOString()}] [System] FastWelcome API (v2.1) listening on port 8081. Powered by EdgeTTS & C# (WMPlayer Native).`);
});
