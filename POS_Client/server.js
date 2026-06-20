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

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    
    if (parsedUrl.pathname === '/welcome' || parsedUrl.pathname === '/speak') {
        let text = "家人";
        if (req.method === 'GET') {
            text = parsedUrl.query.name || parsedUrl.query.text || "家人";
            handleSpeak(text, res, parsedUrl.pathname === '/welcome');
        } else if (req.method === 'POST') {
            let body = '';
            req.on('data', chunk => { body += chunk.toString(); });
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    text = data.name || data.text || "家人";
                } catch(e) {}
                handleSpeak(text, res, parsedUrl.pathname === '/welcome');
            });
        }
    } else {
        res.writeHead(404);
        res.end();
    }
});

async function handleSpeak(text, res, isWelcome) {
    let safeText = text.replace(/['"`$]/g, "").replace(/\(.*?\)/g, "").trim();
    
    try {
        if (!MsEdgeTTS) throw new Error("TTS Module not loaded");
        
        const tts = new MsEdgeTTS();
        await tts.getVoices(); 
        await tts.setMetadata("zh-TW-HsiaoChenNeural", OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);
        
        let textToSpeak = safeText;
        if (isWelcome) {
            let greetingBase64 = "5q2h6L+O5Zue5a62";
            let greeting = Buffer.from(greetingBase64, 'base64').toString('utf8');
            textToSpeak = safeText + " " + greeting;
        }
        
        console.log("Generating audio for text: " + textToSpeak);
        const { audioStream } = tts.toStream(textToSpeak);
        
        const chunks = [];
        audioStream.on('data', chunk => chunks.push(chunk));
        audioStream.on('close', () => {
            const timestamp = Date.now();
            const audioFile = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\current_welcome_" + timestamp + ".mp3";
            fs.writeFileSync(audioFile, Buffer.concat(chunks));
            console.log("Audio generated for:", safeText);
            triggerPopup(isWelcome ? safeText : "", audioFile);
            res.writeHead(200);
            res.end(JSON.stringify({status: "success", text: textToSpeak}));
            
            setTimeout(() => {
                try {
                    if (fs.existsSync(audioFile)) {
                        fs.unlinkSync(audioFile);
                        console.log("Cleaned up old audio file:", audioFile);
                    }
                } catch(e) {}
            }, 60000);
        });
        audioStream.on('error', (err) => {
            console.error("TTS Stream Error:", err);
            triggerPopup("", ""); 
            res.writeHead(500);
            res.end(JSON.stringify({status: "error", message: "TTS stream failed"}));
        });
    } catch(err) {
        console.error("Edge TTS setup error:", err);
        triggerPopup("", ""); 
        res.writeHead(500);
        res.end(JSON.stringify({status: "error", message: err.toString()}));
    }
}

function triggerPopup(name, audioFile) {
    let cmd;
    if (name) {
        let b64Name = Buffer.from(name, 'utf8').toString('base64');
        let scriptPath = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\Welcome.ps1";
        cmd = `powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "${scriptPath}" -Base64Name "${b64Name}" -AudioFile "${audioFile}"`;
    } else {
        // Just play audio without UI popup if it's not a welcome
        let scriptPath = "C:\\\\Users\\\\magic\\\\WelcomeAPI\\\\Welcome.ps1";
        cmd = `powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "${scriptPath}" -AudioFile "${audioFile}" -HideUI`;
    }
    
    exec(cmd, (error) => {
        if (error) console.error("Error launching UI/Audio:", error);
    });
}

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
    console.log('Standalone Native Welcome/Chat API listening on port 8081 with Crash Protection');
});
