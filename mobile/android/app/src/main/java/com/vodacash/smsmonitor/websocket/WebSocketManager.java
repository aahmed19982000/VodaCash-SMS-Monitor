package com.vodacash.smsmonitor.websocket;

import android.util.Log;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;
import java.util.concurrent.atomic.AtomicBoolean;

import android.content.Context;
import android.content.SharedPreferences;
import com.vodacash.smsmonitor.SettingsActivity;

/**
 * إدارة اتصال WebSocket مع تطبيق سطح المكتب.
 */
public class WebSocketManager {

    private static final String TAG = "VodaCash_WS";
    private Context context;

    private WebSocketClient client;
    private final AtomicBoolean connected = new AtomicBoolean(false);

    private final Runnable onConnected;
    private final OnDisconnected onDisconnected;
    private final OnMessage onMessage;

    public interface OnDisconnected { void onDisconnected(String reason); }
    public interface OnMessage { void onMessage(String message); }

    public WebSocketManager(Context context, Runnable onConnected, OnDisconnected onDisconnected, OnMessage onMessage) {
        this.context = context;
        this.onConnected = onConnected;
        this.onDisconnected = onDisconnected;
        this.onMessage = onMessage;
    }

    private String getWsUrl() {
        SharedPreferences prefs = context.getSharedPreferences(SettingsActivity.PREFS_NAME, Context.MODE_PRIVATE);
        String host = prefs.getString(SettingsActivity.KEY_HOST, "192.168.1.100");
        String port = prefs.getString(SettingsActivity.KEY_PORT, "8765");
        return "ws://" + host + ":" + port;
    }

    public void connect() {
        try {
            String url = getWsUrl();
            Log.i(TAG, "Connecting to " + url);
            URI uri = new URI(url);
            client = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshake) {
                    Log.i(TAG, "🟢 Connected to desktop");
                    connected.set(true);
                    if (onConnected != null) onConnected.run();
                }

                @Override
                public void onMessage(String message) {
                    if (onMessage != null) onMessage.onMessage(message);
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    Log.w(TAG, "🔴 Disconnected: " + reason);
                    connected.set(false);
                    if (onDisconnected != null) onDisconnected.onDisconnected(reason);
                }

                @Override
                public void onError(Exception ex) {
                    Log.e(TAG, "❌ WS Error: " + ex.getMessage());
                    connected.set(false);
                }
            };
            client.connect();
        } catch (Exception e) {
            Log.e(TAG, "❌ Connection failed: " + e.getMessage());
        }
    }

    public void reconnect() {
        disconnect();
        connect();
    }

    public void disconnect() {
        if (client != null) {
            try { client.close(); } catch (Exception ignored) {}
            connected.set(false);
        }
    }

    public void send(String message) {
        if (client != null && connected.get()) {
            client.send(message);
        }
    }

    public void sendHeartbeat() {
        send("{\"type\":\"HEARTBEAT\",\"payload\":{}}");
    }

    public boolean isConnected() {
        return connected.get();
    }
}
