import { useAuth } from "./components/Auth";
import { Layout } from "./components/Layout";
import { Empty, Loading } from "./components/ui";
import { useRoute } from "./lib/router";
import { AdminPage } from "./pages/AdminPage";
import { CoachPage } from "./pages/CoachPage";
import { CoachUserPage } from "./pages/CoachUserPage";
import { CoachWorkoutPage } from "./pages/CoachWorkoutPage";
import { ExercisePage } from "./pages/ExercisePage";
import { ExercisesPage } from "./pages/ExercisesPage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProgramPage } from "./pages/ProgramPage";
import { ProgramsPage } from "./pages/ProgramsPage";
import { ProgressPage } from "./pages/ProgressPage";
import { SchedulePage } from "./pages/SchedulePage";
import { TodayPage } from "./pages/TodayPage";
import { WorkoutPage } from "./pages/WorkoutPage";

export function App() {
  const { user, checking } = useAuth();
  const route = useRoute();

  if (checking) return <Loading />;
  if (!user) return <LoginPage />;

  let page;

  switch (route.name) {
    case "today":
      page = <TodayPage />;
      break;
    case "workout":
      page = <WorkoutPage key={route.id} id={route.id} />;
      break;
    case "schedule":
      page = <SchedulePage />;
      break;
    case "programs":
      page = <ProgramsPage />;
      break;
    case "program":
      page = <ProgramPage key={route.id} id={route.id} />;
      break;
    case "exercises":
      page = <ExercisesPage />;
      break;
    case "exercise":
      page = <ExercisePage key={route.id} id={route.id} />;
      break;
    case "progress":
      page = <ProgressPage />;
      break;
    case "profile":
      page = <ProfilePage />;
      break;
    case "admin":
      page = user.is_admin ? (
        <AdminPage table={route.table} />
      ) : (
        <Empty title="Раздел только для администратора">
          <a href="#/">На главную</a>
        </Empty>
      );
      break;
    case "coach":
    case "coachUser":
    case "coachWorkout":
      if (user.role !== "coach") {
        page = (
          <Empty title="Раздел только для тренера">
            <a href="#/">На главную</a>
          </Empty>
        );
      } else if (route.name === "coach") {
        page = <CoachPage />;
      } else if (route.name === "coachUser") {
        page = <CoachUserPage key={route.id} id={route.id} />;
      } else {
        page = (
          <CoachWorkoutPage
            key={`${route.id}-${route.workoutId}`}
            id={route.id}
            workoutId={route.workoutId}
          />
        );
      }
      break;
    default:
      page = (
        <Empty title="Такой страницы нет">
          <a href="#/">На главную</a>
        </Empty>
      );
  }

  return <Layout route={route}>{page}</Layout>;
}
