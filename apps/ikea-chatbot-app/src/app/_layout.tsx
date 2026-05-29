// —— Modules ——
import { Stack } from 'expo-router';

// —— Layout ——
export const unstable_settings = {
    initialRouteName: '(app)',
};

// —— Style ——
import './../style/global.css';

const AppLayout = () => {
    return (
        <>
            <Stack screenOptions={{ headerShown: false }}>
                <Stack.Screen name="(app)" options={{ headerShown: false }} />
            </Stack>
        </>
    );
};

export default AppLayout;
