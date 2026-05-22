import React, { useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

export default function HomeScreen() {

  return (
    <SafeAreaView className="flex-1 bg-[#f9f4fe]">
      <ScrollView
        className="flex-1 px-4 pt-4"
        contentContainerClassName="pb-10"
      >
        <View className="mb-4 flex-row items-center justify-between">
          <Text className="text-2xl font-bold text-slate-900">IKEA Chatbot</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
