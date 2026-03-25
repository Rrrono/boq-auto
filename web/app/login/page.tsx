import { LoginForm } from "../../components/login-form";


export default function LoginPage() {
  return (
    <div className="centeredPanel">
      <section className="card authCard">
        <span className="pill">Secure Access</span>
        <h2 className="headline">Sign in to the BOQ AUTO workspace.</h2>
        <p className="lead">
          This is the first step toward a controlled internal platform. For now, Firebase Auth protects the hosted
          frontend experience before we add backend token enforcement.
        </p>
        <LoginForm />
      </section>
    </div>
  );
}
