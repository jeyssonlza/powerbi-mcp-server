# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-06-08

### Added
- **66 MCP tools** across 8 specialized domains
- **Modular architecture**: server.py refactored from 1,849 to 182 lines
- 8 tool modules: project, model, ai, visuals, analysis, docs, security, pbi_api
- Full Docker + Docker Compose support
- GitHub Actions CI/CD pipeline (Python 3.10 → 3.14 matrix)
- GitHub Actions Release workflow (auto-publish to PyPI)
- OAuth2 test suite (15+ tests with MSAL mocking)
- Performance baseline tests (16+ tests with Enterprise SLAs)
- ReadTheDocs documentation site
- MCP Registry manifest
- pytest coverage >= 75% enforcement

### Tools Inventory
| Domain | Count | Tools |
|--------|-------|-------|
| Project | 11 | project_info, project_structure, project_create, project_read, project_update_metadata, project_list, project_export_pbix, project_import_pbip, project_backup, project_restore_backup, project_delete |
| Model | 23 | table_create, table_list, table_read, table_update, table_delete, table_add_partition, table_set_calculation_group, column_create, column_list, column_update, column_delete, column_add_format, measure_create, measure_list, measure_update, measure_delete, measure_validate_dax, relationship_create, relationship_list, relationship_update, relationship_delete, model_info, model_validate |
| AI & ML | 8 | ai_detect_anomalies, ai_clustering_kmeans, ai_clustering_hierarchical, ai_forecasting_arima, ai_forecasting_exponential, ai_segmentation_rfm, ai_correlation_pearson, ai_correlation_spearman |
| Visuals | 7 | visual_create_page, visual_add_chart, visual_add_table, visual_add_matrix, visual_apply_theme, visual_export_html, visual_generate_report |
| Analysis | 5 | analysis_data_quality, analysis_profile_data, analysis_detect_patterns, analysis_performance_metrics, analysis_suggest_optimizations |
| Docs | 3 | docs_generate_markdown, docs_generate_html, docs_generate_data_dictionary |
| Security | 6 | security_mask_pii, security_hash_column, security_encrypt_file, security_decrypt_file, security_audit_log_read, security_backup_project |
| Power BI API | 5 | pbi_list_workspaces, pbi_list_datasets, pbi_list_reports, pbi_execute_dax, pbi_refresh_dataset |

[0.1.0]: https://github.com/jeyssonzerpa/powerbi-mcp-server/releases/tag/v0.1.0
