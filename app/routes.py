import json
import malariagen_data
import pandas as pd
import plotly
import traceback
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, current_app
from app.auth import oauth, init_oauth
from app.engine import NLPEngine
from google.oauth2.credentials import Credentials

main_bp = Blueprint("main", __name__)

_oauth_initialized = False
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = NLPEngine(api_key=current_app.config["GEMINI_API_KEY"])
    return _engine


def generate_code_snippet(dataset_name, method_name, params, plot_method=None, plot_params=None):
    lines = ["import malariagen_data", ""]
    var_name = dataset_name.lower()
    lines.append(f"{var_name} = malariagen_data.{dataset_name}()")

    param_parts = []
    for k, v in params.items():
        if isinstance(v, str):
            param_parts.append(f'{k}="{v}"')
        else:
            param_parts.append(f"{k}={v}")
    param_str = ", ".join(param_parts)
    lines.append(f"result = {var_name}.{method_name}({param_str})")
    lines.append("result")

    if plot_method:
        plot_parts = ["result"]
        if plot_params:
            for k, v in plot_params.items():
                if isinstance(v, str):
                    plot_parts.append(f'{k}="{v}"')
                else:
                    plot_parts.append(f"{k}={v}")
        lines.append(f"\nfig = {var_name}.{plot_method}({', '.join(plot_parts)})")
        lines.append("fig.show()")

    return "\n".join(lines)


@main_bp.before_app_request
def ensure_oauth():
    global _oauth_initialized
    if not _oauth_initialized:
        init_oauth(current_app)
        _oauth_initialized = True


@main_bp.route("/")
def index():
    if "user" in session:
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@main_bp.route("/login")
def login():
    redirect_uri = "https://5000-firebase-nlp-flask-app-1774185695832.cluster-zkm2jrwbnbd4awuedc2alqxrpk.cloudworkstations.dev/callback"
    return oauth.google.authorize_redirect(redirect_uri)


@main_bp.route("/callback")
def callback():
    token = oauth.google.authorize_access_token()
    session["user"] = token.get("userinfo")
    session["access_token"] = token.get("access_token")
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("main.index"))
    return render_template("dashboard.html", user=session["user"])


def execute_llm_response(data_instance, llm_response, code_snippet):
    method_name = llm_response["method"]
    params = llm_response.get("parameters", {})
    plot_method = llm_response.get("plot_method")
    plot_params = llm_response.get("plot_parameters") or {}

    if method_name.startswith("plot_"):
        method_fn = getattr(data_instance, method_name)
        fig = method_fn(**params, show=False)
        plot_json = None
        if fig is not None:
            plot_json = json.loads(plotly.io.to_json(fig))
        return {
            "llm_response": llm_response,
            "code_snippet": code_snippet,
            "result_html": None,
            "result_type": "Figure",
            "row_count": None,
            "plot_json": plot_json,
        }

    method_fn = getattr(data_instance, method_name)
    result = method_fn(**params)

    result_html = None
    result_type = type(result).__name__

    if isinstance(result, pd.DataFrame):
        result_html = result.head(100).to_html(
            classes="data-table", index=False, border=0, na_rep="-"
        )
    else:
        try:
            df = pd.DataFrame(result)
            result_html = df.head(100).to_html(
                classes="data-table", index=False, border=0, na_rep="-"
            )
            result_type = "DataFrame (converted)"
        except Exception:
            result_html = f"<pre>{str(result)[:5000]}</pre>"

    plot_json = None
    if plot_method:
        try:
            plot_fn = getattr(data_instance, plot_method)
            fig = plot_fn(result, **plot_params, show=False)
            if fig is not None:
                plot_json = json.loads(plotly.io.to_json(fig))
        except Exception as plot_err:
            plot_json = {"error": str(plot_err)}

    return {
        "llm_response": llm_response,
        "code_snippet": code_snippet,
        "result_html": result_html,
        "result_type": result_type,
        "row_count": len(result) if hasattr(result, "__len__") else None,
        "plot_json": plot_json,
    }


@main_bp.route("/query", methods=["POST"])
def query():
    if "user" not in session:
        return jsonify({"error": "Authentication required. Please sign in first."}), 401

    user_query = request.json.get("query", "")
    if not user_query.strip():
        return jsonify({"error": "Query string cannot be empty."}), 400

    session_id = session["user"].get("email", "default")

    try:
        engine = get_engine()
        llm_response = engine.process_query(user_query, session_id=session_id)

        dataset_name = llm_response["dataset"]
        method_name = llm_response["method"]
        params = llm_response.get("parameters", {})
        plot_method = llm_response.get("plot_method")
        plot_params = llm_response.get("plot_parameters")

        code_snippet = generate_code_snippet(
            dataset_name, method_name, params, plot_method, plot_params
        )


        access_token = session.get("access_token")
        credentials = Credentials(token=access_token)
        data_instance = getattr(malariagen_data, dataset_name)(token=credentials)

        response_data = execute_llm_response(
            data_instance, llm_response, code_snippet
        )
        return jsonify(response_data)

    except Exception as first_error:
        try:
            engine = get_engine()
            retry_response = engine.process_query(
                f"My previous query was: '{user_query}'. "
                f"It failed with error: {str(first_error)}. "
                f"Please fix the parameters and try a different approach.",
                session_id=session_id
            )

            dataset_name = retry_response["dataset"]
            method_name = retry_response["method"]
            params = retry_response.get("parameters", {})

            code_snippet = generate_code_snippet(
                dataset_name, method_name, params,
                retry_response.get("plot_method"),
                retry_response.get("plot_parameters")
            )

            access_token = session.get("access_token")
            credentials = Credentials(token=access_token)
            data_instance = getattr(malariagen_data, dataset_name)(token=credentials)

            response_data = execute_llm_response(
                data_instance, retry_response, code_snippet
            )
            response_data["retried"] = True
            return jsonify(response_data)

        except Exception as retry_error:
            traceback.print_exc()
            return jsonify({
                "error": f"Query failed: {str(first_error)}",
                "retry_error": f"Retry also failed: {str(retry_error)}"
            }), 500


@main_bp.route("/clear-history", methods=["POST"])
def clear_history():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    session_id = session["user"].get("email", "default")
    engine = get_engine()
    engine.clear_history(session_id)
    return jsonify({"status": "ok"})


@main_bp.route("/export-csv", methods=["POST"])
def export_csv():
    if "user" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        html_table = request.json.get("table_html", "")
        dfs = pd.read_html(html_table)
        if dfs:
            csv_data = dfs[0].to_csv(index=False)
            return jsonify({"csv": csv_data})
        return jsonify({"error": "No table data found"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@main_bp.route("/logout")
def logout():
    session_id = session.get("user", {}).get("email", "default")
    engine = get_engine()
    engine.clear_history(session_id)
    session.clear()
    return redirect(url_for("main.index"))
