package de.avento.app.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import de.avento.app.AppContainer
import de.avento.app.data.network.toGermanMessage
import de.avento.app.ui.auth.AuthViewModel
import de.avento.app.ui.auth.LoginScreen
import de.avento.app.ui.auth.PasswordResetScreen
import de.avento.app.ui.auth.RegistrationMode
import de.avento.app.ui.auth.RegistrationScreen
import de.avento.app.ui.dashboard.DashboardScreen
import de.avento.app.ui.dashboard.DashboardViewModel
import de.avento.app.ui.detail.DetailScreen
import de.avento.app.ui.detail.DetailViewModel
import kotlinx.coroutines.flow.map

private object Routes {
    const val Login = "login"
    const val Register = "register"
    const val Bootstrap = "bootstrap"
    const val PasswordReset = "password-reset"
    const val Dashboard = "dashboard"
    const val Detail = "activity/{activityId}"
    fun detail(id: String) = "activity/$id"
}

@Composable
fun AventoApp(container: AppContainer) {
    val initiallyAuthenticated by produceState<Boolean?>(null, container.repository) {
        value = runCatching { container.repository.currentSession() != null }.getOrDefault(false)
    }
    if (initiallyAuthenticated == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }

    val navController = rememberNavController()
    val sessionPresent by container.repository.session.map { it != null }
        .collectAsStateWithLifecycle(initialValue = initiallyAuthenticated == true)
    LaunchedEffect(sessionPresent) {
        if (!sessionPresent && navController.currentDestination?.route !in setOf(
                Routes.Login,
                Routes.Register,
                Routes.Bootstrap,
                Routes.PasswordReset,
            )
        ) {
            navController.navigate(Routes.Login) { popUpTo(0) }
        }
    }
    val errorMapper: (Throwable) -> String = { it.toGermanMessage(container.errorMoshi) }
    NavHost(
        navController = navController,
        startDestination = if (initiallyAuthenticated == true) Routes.Dashboard else Routes.Login,
    ) {
        composable(Routes.Login) {
            val vm: AuthViewModel = viewModel(factory = SimpleViewModelFactory {
                AuthViewModel(container.repository, errorMapper)
            })
            LoginScreen(
                viewModel = vm,
                onLoggedIn = { navController.navigate(Routes.Dashboard) { popUpTo(Routes.Login) { inclusive = true } } },
                onRegister = { navController.navigate(Routes.Register) },
                onResetPassword = { navController.navigate(Routes.PasswordReset) },
                onBootstrap = { navController.navigate(Routes.Bootstrap) },
            )
        }
        composable(Routes.PasswordReset) {
            val vm: AuthViewModel = viewModel(factory = SimpleViewModelFactory {
                AuthViewModel(container.repository, errorMapper)
            })
            PasswordResetScreen(
                viewModel = vm,
                onBack = { navController.popBackStack() },
                onReturnToLogin = { navController.popBackStack() },
            )
        }
        composable(Routes.Register) {
            val vm: AuthViewModel = viewModel(factory = SimpleViewModelFactory {
                AuthViewModel(container.repository, errorMapper)
            })
            RegistrationScreen(
                mode = RegistrationMode.Invitation,
                viewModel = vm,
                onComplete = { navController.navigate(Routes.Dashboard) { popUpTo(Routes.Login) { inclusive = true } } },
                onBack = { navController.popBackStack() },
            )
        }
        composable(Routes.Bootstrap) {
            val vm: AuthViewModel = viewModel(factory = SimpleViewModelFactory {
                AuthViewModel(container.repository, errorMapper)
            })
            RegistrationScreen(
                mode = RegistrationMode.Bootstrap,
                viewModel = vm,
                onComplete = { navController.navigate(Routes.Dashboard) { popUpTo(Routes.Login) { inclusive = true } } },
                onBack = { navController.popBackStack() },
            )
        }
        composable(Routes.Dashboard) {
            val vm: DashboardViewModel = viewModel(factory = SimpleViewModelFactory {
                DashboardViewModel(container.repository, errorMapper)
            })
            val pendingImport by container.pendingImport.collectAsStateWithLifecycle()
            DashboardScreen(
                viewModel = vm,
                pendingImport = pendingImport,
                onImportOffered = container::offerImport,
                onImportConsumed = container::consumeImport,
                onOpenActivity = { navController.navigate(Routes.detail(it)) },
                onLoggedOut = {
                    navController.navigate(Routes.Login) { popUpTo(Routes.Dashboard) { inclusive = true } }
                },
            )
        }
        composable(
            route = Routes.Detail,
            arguments = listOf(navArgument("activityId") { type = NavType.StringType }),
        ) { entry ->
            val id = requireNotNull(entry.arguments?.getString("activityId"))
            val vm: DetailViewModel = viewModel(factory = SimpleViewModelFactory {
                DetailViewModel(id, container.repository, errorMapper)
            })
            DetailScreen(
                viewModel = vm,
                onBack = { navController.popBackStack() },
                onDeleted = {
                    navController.navigate(Routes.Dashboard) {
                        popUpTo(Routes.Dashboard) { inclusive = true }
                    }
                },
            )
        }
    }
}
