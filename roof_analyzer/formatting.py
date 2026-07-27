"""Formatação do resultado da API para exibição na interface."""


def format_result(payload: dict) -> str:
    """Transforma a resposta da API no texto exibido ao usuário."""
    result = payload.get("result", {})
    condition = result.get("roof_condition", {})
    maintenance = result.get("maintenance", {})
    lines = [
        "CONDIÇÃO GERAL",
        f"Pontuação: {condition.get('score', '—')} | Classificação: {condition.get('classification', '—')}",
        condition.get("summary", "Sem resumo disponível."),
        "\nMANUTENÇÃO",
        f"Prioridade: {maintenance.get('priority', '—')}",
        f"Inspeção presencial: {'Sim' if maintenance.get('inspection_required') else 'Não'}",
        f"Risco de vazamento: {maintenance.get('risk_of_leak', '—')}",
        f"Risco estrutural: {maintenance.get('structural_risk', '—')}",
        "\nPROBLEMAS IDENTIFICADOS",
    ]
    for number, issue in enumerate(result.get("issues", []), 1):
        lines += [
            f"\n{number}. {issue.get('type', 'Problema')} — {issue.get('severity', '—')} ({issue.get('confidence', '—')}% confiança)",
            f"Local: {issue.get('location', '—')}",
            f"Descrição: {issue.get('description', '—')}",
            f"Possível causa: {issue.get('possible_cause', '—')}",
            f"Consequência: {issue.get('possible_consequence', '—')}",
            f"Recomendação: {issue.get('recommendation', '—')}",
        ]
    limitations = result.get("limitations", [])
    if limitations:
        lines.append("\nLIMITAÇÕES DA ANÁLISE")
        lines.extend(f"• {item}" for item in limitations)
    return "\n".join(lines)
