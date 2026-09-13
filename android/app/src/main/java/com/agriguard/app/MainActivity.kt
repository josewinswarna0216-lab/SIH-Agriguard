package com.agriguard.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.agriguard.app.network.ServerConfig
import com.agriguard.app.screens.HistoryScreen
import com.agriguard.app.screens.IrrigationScreen
import com.agriguard.app.screens.LiveScreen
import com.agriguard.app.screens.MissionPlanScreen
import com.agriguard.app.ui.theme.AgriGuardTheme

private enum class Tab(val route: String, val label: String) {
    Live("live", "Live"),
    Positions("positions", "Flight Plan"),
    History("history", "Results"),
    Irrigation("irrigation", "Irrigation"),
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        ServerConfig.load(this)
        setContent {
            AgriGuardTheme {
                AgriGuardApp()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgriGuardApp() {
    val navController = rememberNavController()
    var showSettings by remember { mutableStateOf(false) }

    if (showSettings) {
        SettingsDialog(onDismiss = { showSettings = false })
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AgriGuard") },
                actions = {
                    IconButton(onClick = { showSettings = true }) {
                        Icon(Icons.Filled.Settings, contentDescription = "Server settings")
                    }
                    IconButton(onClick = { AppLanguage.toggle() }) {
                        Text(if (AppLanguage.current == "en") "EN" else "TA")
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
                val backStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = backStackEntry?.destination

                Tab.entries.forEach { tab ->
                    val selected = currentDestination?.hierarchy?.any { it.route == tab.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tabIcon(tab), contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Tab.Live.route,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable(Tab.Live.route) { LiveScreen() }
            composable(Tab.Positions.route) { MissionPlanScreen() }
            composable(Tab.History.route) { HistoryScreen() }
            composable(Tab.Irrigation.route) { IrrigationScreen() }
        }
    }
}

private fun tabIcon(tab: Tab) = when (tab) {
    Tab.Live -> Icons.Filled.Videocam
    Tab.Positions -> Icons.Filled.Map
    Tab.History -> Icons.Filled.History
    Tab.Irrigation -> Icons.Filled.WaterDrop
}
