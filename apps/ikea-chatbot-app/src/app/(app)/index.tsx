import React, { useState, useRef, useEffect } from "react";
import API from "../../core/networking/api";
import {
  Text,
  View,
  Image,
  ScrollView,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  Linking,
  Animated,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "@ikea_chat_history";
const SESSION_KEY = "@ikea_chat_session_id";

function TypingIndicator() {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const createAnimation = (dot, delay) => {
      return Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, { toValue: -6, duration: 300, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0, duration: 300, useNativeDriver: true }),
          Animated.delay(400),
        ])
      );
    };

    const anim1 = createAnimation(dot1, 0);
    const anim2 = createAnimation(dot2, 150);
    const anim3 = createAnimation(dot3, 300);

    Animated.parallel([anim1, anim2, anim3]).start();

    return () => {
      anim1.stop();
      anim2.stop();
      anim3.stop();
    };
  }, [dot1, dot2, dot3]);

  return (
    <View className="flex-row items-start mb-4">
      <View className="w-9 h-9 rounded-full bg-[#0051BA] justify-center items-center mr-2 mt-1">
        <Text className="text-lg">🤖</Text>
      </View>
      <View className="bg-[#F0F0F0] rounded-2xl rounded-bl-[4px] px-5 py-[14px] flex-row items-center justify-center space-x-1.5 h-11">
        <Animated.View style={{ transform: [{ translateY: dot1 }] }} className="w-[7px] h-[7px] rounded-full bg-[#888888] mx-[2px]" />
        <Animated.View style={{ transform: [{ translateY: dot2 }] }} className="w-[7px] h-[7px] rounded-full bg-[#888888] mx-[2px]" />
        <Animated.View style={{ transform: [{ translateY: dot3 }] }} className="w-[7px] h-[7px] rounded-full bg-[#888888] mx-[2px]" />
      </View>
    </View>
  );
}

export default function HomeScreen() {
  const scrollViewRef = useRef(null);
  const [inputText, setInputText] = useState("");
  const [messages, setMessages] = useState([]);
  const [isBotTyping, setIsBotTyping] = useState(false);
  const [sessionId, setSessionId] = useState("");

  // Initialiseer chathistorie en behoud een vaste sessie-id tegen geheugenverlies
  useEffect(() => {
    const initializeChat = async () => {
      try {
        const savedChat = await AsyncStorage.getItem(STORAGE_KEY);
        let savedSession = await AsyncStorage.getItem(SESSION_KEY);

        if (!savedSession) {
          savedSession = `session-${Date.now()}`;
          await AsyncStorage.setItem(SESSION_KEY, savedSession);
        }
        
        setSessionId(savedSession);
        setMessages(savedChat !== null ? JSON.parse(savedChat) : []);
      } catch (error) {
        console.error("Initialisatie mislukt:", error);
        setMessages([]);
      }
    };
    initializeChat();
  }, []);

  // Synchroniseer historie met lokale opslag
  useEffect(() => {
    const saveChatHistory = async () => {
      try {
        if (messages.length > 0) {
          await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
        }
      } catch (error) {
        console.error("Opslaan mislukt:", error);
      }
    };
    saveChatHistory();
  }, [messages]);

  const postMessage = async (messageContent) => {
    setIsBotTyping(true);
    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const botMessageId = `${Date.now()}-bot-ai-${Math.random().toString(36).substr(2, 4)}`;

    try {
      console.log("🚀 Verzenden naar chatbot API...");
      const response = await API.post('/chat', {
        session_id: sessionId || `session-${Date.now()}`,
        message: messageContent,
      });

      const data = response.data;
      const botReply = data?.response_message || "Bericht succesvol verwerkt!";
      // Haal de dynamische links op uit de API response payload
      const links = data?.reference_hrefs || null;

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: botMessageId,
          sender: "bot",
          type: "text",
          content: botReply,
          timestamp: currentTime,
          reference_hrefs: links, // Sla de linkjes op in de bericht-state
        }
      ]);

    } catch (error) {
      console.error("🔴 Netwerk Fout:", error);
      const foutMelding = error.response?.data?.detail || error.message;

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: botMessageId,
          sender: "bot",
          type: "text",
          content: `❌ Netwerkfout: ${foutMelding}. Controleer de verbinding.`,
          timestamp: currentTime,
        },
      ]);
    } finally {
      setIsBotTyping(false);
    }
  };

  const handleSend = () => {
    const cleanText = inputText.trim();
    if (cleanText.length === 0) return;

    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessageId = `${Date.now()}-user-${Math.random().toString(36).substr(2, 4)}`;

    setMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        sender: "user",
        type: "text",
        content: cleanText,
        timestamp: currentTime,
      },
    ]);
    
    setInputText("");
    postMessage(cleanText);
  };

  const clearChatHistory = async () => {
    try {
      await AsyncStorage.removeItem(STORAGE_KEY);
      await AsyncStorage.removeItem(SESSION_KEY);
      const newSession = `session-${Date.now()}`;
      await AsyncStorage.setItem(SESSION_KEY, newSession);
      
      setSessionId(newSession);
      setMessages([]);
      setIsBotTyping(false);
    } catch (error) {
      console.error("Wissen mislukt:", error);
    }
  };

  const handleLinkPress = (url) => {
    Linking.openURL(url).catch((err) => console.error("Link openen mislukt:", err));
  };

  return (
    <View className="flex-1 bg-white">
      <StatusBar barStyle="dark-content" />

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1"
      >
        {/* --- HEADER --- */}
        <SafeAreaView className="bg-white" edges={["top"]}>
          <View className="flex-row items-center justify-between px-4 py-3 border-b border-[#EAEAEA]">
            <TouchableOpacity className="p-1">
              <Text className="text-3xl text-[#0051BA] font-light">‹</Text>
            </TouchableOpacity>

            <View className="flex-row items-center flex-1 ml-3">
              <View className="w-10 h-10 rounded-full bg-[#0051BA] justify-center items-center">
                <Text className="text-[#FFDA1A] font-bold text-[11px]">IKEA</Text>
              </View>
              <View className="ml-[10px]">
                <View className="flex-row items-center">
                  <Text className="text-base font-bold text-[#333333]">IKEA Assistent</Text>
                  <View className="bg-[#0051BA] rounded-[6px] w-[13px] h-[13px] justify-center items-center ml-1">
                    <Text className="text-white text-[8px] font-bold">✓</Text>
                  </View>
                </View>
                <Text className="text-xs text-[#666666] mt-0.5">Altijd hier om te helpen</Text>
              </View>
            </View>

            <TouchableOpacity onPress={clearChatHistory} className="p-2 active:opacity-50">
              <Text className="text-xl text-[#0051BA]">ⓘ</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>

        {/* --- CHAT BODY --- */}
        <ScrollView
          ref={scrollViewRef}
          className="flex-1 bg-[#F9F9F9]"
          contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 24 }}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          <Text className="text-center text-[#888888] text-xs my-[10px]">Vandaag</Text>

          {messages.map((item, index) => {
            const renderKey = item.id ? item.id : `msg-render-${index}`;

            if (item.sender === "user") {
              return (
                <View key={renderKey} className="items-end mb-2">
                  <View className="bg-[#0051BA] rounded-2xl rounded-br-[4px] px-[14px] py-[10px] max-w-[85%]">
                    <Text className="text-white text-[15px] leading-5">{item.content}</Text>
                    <Text className="text-white/70 text-[10px] text-right mt-1">{item.timestamp} ✓✓</Text>
                  </View>
                </View>
              );
            }

            if (item.sender === "bot") {
              return (
                <View key={renderKey} className="mb-4">
                  {/* Het tekstballonnetje van de bot */}
                  <View className="flex-row items-start">
                    <View className="w-9 h-9 rounded-full bg-[#0051BA] justify-center items-center mr-2 mt-1">
                      <Text className="text-lg">🤖</Text>
                    </View>
                    <View className="bg-[#F0F0F0] rounded-2xl rounded-bl-[4px] px-[14px] py-3 max-w-[80%]">
                      <Text className="text-[#333333] text-[15px] leading-[21px]">{item.content}</Text>
                      <Text className="text-[#999999] text-[10px] mt-1">{item.timestamp}</Text>
                    </View>
                  </View>

                  {/* --- FIX: DYNAMISCHE LINK-KNOPPEN RENDEREN --- */}
                  {item.reference_hrefs && item.reference_hrefs.length > 0 && (
                    <View className="ml-11 mt-2 gap-2 max-w-[80%]">
                      {item.reference_hrefs.map((link, lIdx) => (
                        <TouchableOpacity
                          key={`link-${lIdx}`}
                          onPress={() => handleLinkPress(link.href)}
                          className="bg-white border border-[#0051BA] rounded-xl p-3 flex-row items-center justify-between active:bg-[#0051BA]/5 shadow-sm"
                        >
                          <View className="flex-1 mr-2">
                            <Text className="text-[#0051BA] font-bold text-[14px]">{link.title}</Text>
                            {link.description ? (
                              <Text className="text-[#666666] text-xs mt-0.5" numberOfLines={1}>{link.description}</Text>
                            ) : null}
                          </View>
                          <Text className="text-[#0051BA] font-bold text-lg">›</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  )}
                </View>
              );
            }
            return null;
          })}

          {isBotTyping && <TypingIndicator />}
        </ScrollView>

        {/* --- INPUT BAR --- */}
        <SafeAreaView className="bg-white" edges={["bottom"]}>
          <View className="flex-row items-center px-3 py-[10px] border-t border-[#EAEAEA]">
            <TouchableOpacity className="w-9 h-9 rounded-full bg-[#0051BA] justify-center items-center">
              <Text className="text-white text-2xl font-light mt-[-2px]">+</Text>
            </TouchableOpacity>

            <TextInput
              className="flex-1 h-10 bg-[#F5F5F5] rounded-full px-4 mx-[10px] text-[15px] text-[#333333]"
              placeholder="Typ een bericht..."
              placeholderTextColor="#999"
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={handleSend}
              returnKeyType="send"
            />

            <TouchableOpacity className="w-9 h-9 justify-center items-center" onPress={handleSend}>
              <Text className={`text-[#0051BA] text-2xl ${inputText.trim().length === 0 ? "opacity-30" : "opacity-100"}`}>
                ➔
              </Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </View>
  );
}