#!/usr/bin/env python3
"""
Deploy trained model ke Ollama (VPS)
====================================

Usage:
    python deploy_to_ollama.py --gguf ./migancore-identity.q4_k_m.gguf --tag migancore:0.8-clean

Steps:
    1. Copy GGUF ke VPS /opt/ado/data/ollama/models/
    2. Create Modelfile
    3. ollama create
    4. ollama run test
    5. Update API config
"""

import argparse, subprocess, sys, json, os
from pathlib import Path


def run(cmd, check=True):
    print(f'$ {cmd}')
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        print(f'ERROR: Command failed with code {result.returncode}', file=sys.stderr)
        sys.exit(1)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gguf', required=True, help='Path ke GGUF file')
    parser.add_argument('--tag', default='migancore:0.8-clean')
    parser.add_argument('--api-config', default='/opt/ado/migancore/api/config.py')
    parser.add_argument('--agents-json', default='/opt/ado/migancore/api/agents.json')
    parser.add_argument('--docker-compose', default='/opt/ado/docker-compose.yml')
    parser.add_argument('--test', action='store_true', help='Run identity test after deploy')
    args = parser.parse_args()

    gguf_path = Path(args.gguf).resolve()
    if not gguf_path.exists():
        print(f'ERROR: GGUF file tidak ditemukan: {gguf_path}', file=sys.stderr)
        sys.exit(1)

    print('=' * 72)
    print('DEPLOY TO OLLAMA')
    print('=' * 72)
    print(f'GGUF     : {gguf_path}')
    print(f'Tag      : {args.tag}')
    print()

    # 1. Copy GGUF ke ollama models dir
    ollama_models = Path('/opt/ado/data/ollama/models')
    ollama_models.mkdir(parents=True, exist_ok=True)
    dest = ollama_models / gguf_path.name
    print(f'[1/5] Copy GGUF ke {dest}...')
    run(f'cp "{gguf_path}" "{dest}"')

    # 2. Create Modelfile
    modelfile = ollama_models / 'Modelfile'
    print(f'[2/5] Create Modelfile...')
    with open(modelfile, 'w') as f:
        f.write(f'FROM {dest}\n')
        f.write('\n')
        f.write('# Identitas Mighan-Core sudah di-embed di weights\n')
        f.write('# System prompt opsional — model tetap kenal diri tanpa system prompt\n')
        f.write('PARAMETER temperature 0.7\n')
        f.write('PARAMETER top_p 0.9\n')
        f.write('PARAMETER top_k 40\n')
        f.write('PARAMETER num_ctx 8192\n')
        f.write('PARAMETER repeat_penalty 1.1\n')
        f.write('\n')
        f.write('TEMPLATE """{{- if .System }}<|im_start|>system\n')
        f.write('{{ .System }}<|im_end|>\n')
        f.write('{{ end }}{{- if .Prompt }}<|im_start|>user\n')
        f.write('{{ .Prompt }}<|im_end|>\n')
        f.write('{{ end }}<|im_start|>assistant\n')
        f.write('{{ .Response }}<|im_end|>"""\n')

    # 3. ollama create
    print(f'[3/5] ollama create {args.tag}...')
    run(f'ollama create {args.tag} -f {modelfile}')

    # 4. Test
    print(f'[4/5] Quick test...')
    test_result = run(f'ollama run {args.tag} "Siapa kamu? Jelaskan dalam satu kalimat."', check=False)
    response = test_result.stdout.strip()
    print(f'Response: {response}')

    if 'mighan' in response.lower() or 'tiranyx' in response.lower():
        print('✅ Identity test PASSED')
    else:
        print('⚠️  Identity test WARNING — response tidak mengandung "mighan" atau "tiranyx"')
        print('   Model mungkin butuh fine-tuning lebih kuat atau system prompt.')

    # 5. Update config files
    print(f'[5/5] Update config files...')

    # Update config.py
    if Path(args.api_config).exists():
        with open(args.api_config, 'r') as f:
            config_content = f.read()
        # Replace model references
        import re
        config_content = re.sub(
            r'migancore:0\.[0-9]+[a-z]?',
            args.tag,
            config_content
        )
        with open(args.api_config, 'w') as f:
            f.write(config_content)
        print(f'  Updated: {args.api_config}')

    # Update agents.json
    if Path(args.agents_json).exists():
        with open(args.agents_json, 'r') as f:
            agents = json.load(f)
        for agent in agents.get('agents', []):
            if 'model' in agent:
                agent['model'] = args.tag
        with open(args.agents_json, 'w') as f:
            json.dump(agents, f, indent=2)
        print(f'  Updated: {args.agents_json}')

    # Update docker-compose.yml
    if Path(args.docker-compose).exists():
        with open(args.docker-compose, 'r') as f:
            dc_content = f.read()
        dc_content = re.sub(
            r'migancore:0\.[0-9]+[a-z]?',
            args.tag,
            dc_content
        )
        with open(args.docker-compose, 'w') as f:
            f.write(dc_content)
        print(f'  Updated: {args.docker-compose}')

    print()
    print('=' * 72)
    print('DEPLOYMENT COMPLETE')
    print('=' * 72)
    print(f'Model: {args.tag}')
    print(f'GGUF : {dest}')
    print()
    print('Perintah:')
    print(f'  ollama run {args.tag}')
    print(f'  ollama list')
    print()
    print('Rollback jika ada masalah:')
    print(f'  ollama create migancore:0.7c -f /opt/ado/data/ollama/models/Modelfile.0.7c')
    print('=' * 72)


if __name__ == '__main__':
    main()
