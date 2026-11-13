# Custos e analytics

Status: estimativa de planejamento; não é contratação nem orçamento fechado. Pesquisa em 29/10/2026.

## Cenário principal: VPS Hostinger já contratada

O usuário informou custo de R$ 80, considerado mensal pelo contexto da conversa. A captura do painel mostra plano KVM 1, 1 núcleo de CPU, 4 GB de RAM, 50 GB de disco e 4 TB de largura de banda. Mostra também validade em 22/11/2026 e renovação automática ativa; não informa o valor da renovação, periodicidade da franquia de tráfego nem condições de backup. Não presumir esses itens.

O usuário confirmou que essa VPS hospeda o Sycon Suite, mas pretende substituí-lo pelo De Olho na Política. O cenário principal passa a ser uso exclusivo da máquina existente pelo novo projeto. Os R$ 80/mês continuam sendo uma despesa já existente; não haverá acréscimo de hospedagem se o plano atual for suficiente. Não houve acesso ao servidor, retirada do Sycon ou validação de capacidade.

| Item | Impacto no orçamento |
| --- | --- |
| VPS existente | R$ 80/mês já pagos; acréscimo de R$ 0 se não houver upgrade ou nova contratação |
| Domínio | Referência anterior de R$ 40/ano, se for necessário adquirir um domínio elegível; não contratado |
| Analytics e proteção básica | Manter as opções gratuitas propostas, dentro dos limites dos planos |
| Backup externo | Valor pendente da escolha do destino e da retenção; não presumir que o plano Hostinger inclui tudo o que precisamos |
| Manutenção humana | Separada da infraestrutura, conforme seção abaixo |

Com domínio de R$ 40/ano, o custo recorrente conhecido fica em **R$ 83,33/mês equivalentes + backup externo e eventuais adicionais**. Como a VPS já está paga, o custo incremental seria **R$ 3,33/mês equivalentes + backup externo e adicionais**, se a capacidade atual bastar. O domínio é desembolsado anualmente. Com a substituição, os R$ 80 passam a sustentar o novo projeto, sem duplicar a cobrança. Preservação dos backups do Sycon e eventual sobreposição temporária de ambientes devem entrar no planejamento de transição.

Para planejamento, reservar provisoriamente **R$ 100–150/mês no total, incluindo os R$ 80 existentes**, condicionado à capacidade e à cotação do backup. Isso deixa R$ 16,67–66,67 após servidor e domínio para backup e margem; é um envelope de orçamento, não preço de serviço confirmado. Sem upgrade, corresponde a R$ 20–70 adicionais ao gasto atual. Não inclui manutenção humana nem implica aprovação desse teto pelo usuário.

A estimativa anterior de R$ 200–300/mês deixa de ser a recomendação principal: ela pressupunha contratar outra VPS. Permanece abaixo como comparação caso a máquina existente não comporte o projeto.

## Referência alternativa: contratação de nova infraestrutura

Exemplo reproduzível com DigitalOcean e Cloudflare. O fornecedor ainda será escolhido; esta referência permite comparar propostas sem depender de desconto promocional.

| Item | Preço de referência | Fonte ou premissa |
| --- | --- | --- |
| VPS Basic, 2 vCPU e 4 GiB | US$ 24/mês | [DigitalOcean Droplets](https://www.digitalocean.com/pricing/droplets) |
| Backup diário da VPS | US$ 7,20/mês | 30% do servidor, conforme [preços de backups](https://www.digitalocean.com/pricing/backups) |
| Armazenamento de cópias do banco fora da VPS | US$ 5/mês, plano básico | [Spaces](https://docs.digitalocean.com/products/spaces/details/pricing/); isolamento de credenciais e retenção a configurar |
| DNS, CDN e proteção de borda básica | US$ 0 no plano Free | [Planos Cloudflare](https://www.cloudflare.com/plans/); recursos e limites dependem do plano |
| Analytics inicial | US$ 0 | [Cloudflare Web Analytics](https://developers.cloudflare.com/web-analytics/about/) |
| Domínio .br elegível | R$ 40/ano | [Registro.br](https://registro.br/dominio); nome e disponibilidade não verificados |

Total de referência: **US$ 36,20/mês + R$ 40/ano de domínio**. Backup da VPS não substitui cópia consistente do PostgreSQL. Armazenamento fora da VPS protege da perda da máquina; permanecer no mesmo fornecedor não elimina risco de comprometimento da conta. Usar credenciais separadas e cópia adicional periódica sob controle independente.

Para simulação, adotar dólar a R$ 5,50, **apenas hipótese de cálculo, não cotação atual**:

- US$ 36,20 × R$ 5,50 + R$ 40 ÷ 12 = aproximadamente R$ 202,43/mês.
- Acrescentando margem de planejamento de 20%: aproximadamente R$ 242,92/mês.
- Faixa arredondada recomendada para reserva inicial: **R$ 200–300/mês**. Valor anual básico estimado, antes da margem: R$ 2.429,20.

A margem é reserva para variação cambial, taxas e pequenas despesas; não é alíquota tributária. Fatura real depende de câmbio, impostos, franquias, região e consumo. O domínio é pago anualmente, apesar do rateio na comparação.

## Cenários alternativos com nova contratação

| Cenário | Reserva mensal estimada | Hipóteses |
| --- | --- | --- |
| Validação local | Sem contratação de hospedagem | Usa computador e conexão existentes; não é serviço público contínuo |
| Lançamento enxuto | R$ 200–300 | Referência acima, homologação local e sem alta disponibilidade |
| Lançamento com mais margem | R$ 400–600 | Exemplo: VPS de US$ 48, backup diário de US$ 14,40, armazenamento de US$ 5 e Cloudflare Pro mensal de US$ 25: US$ 92,40; com mesmo câmbio, domínio e margem de 15%, cerca de R$ 588/mês |
| Operação ampliada | Orçamento após medição | Banco gerenciado, máquinas separadas, redundância, maior histórico ou tráfego intenso |

O Pro é opcional; [custa US$ 25/mês na cobrança mensal ou US$ 20/mês com cobrança anual](https://www.cloudflare.com/plans/). Não contratar apenas porque existe: verificar quais controles de proteção fazem falta. Mais RAM e plano pago não criam alta disponibilidade.

## O que não está incluído

Desenvolvimento, correções, revisão editorial, suporte, plantão, avaliação jurídica, auditoria externa, publicidade, e-mail profissional, ferramentas pagas de equipe, ambiente permanente de homologação e consumo excedente. Armazenamento independente já existente foi assumido para a cópia adicional periódica; se precisar contratar, incluir na conta.

Planejar inicialmente 4–8 horas humanas/mês para revisão operacional e pequenos ajustes, como hipótese de organização, não garantia. Mudanças nas fontes e incidentes podem exigir mais. Custo total = infraestrutura + horas efetivas × valor/hora acordado + serviços opcionais.

Não há uso de IA paga previsto no fluxo de produção. As fontes selecionadas são de dados públicos; confirmar condições e quotas antes de integrar, sem pressupor disponibilidade ilimitada.

Configurar alertas a 70%, 90% e 100% do orçamento escolhido, onde o fornecedor suportar; manter verificação manual mensal. Alertas não bloqueiam automaticamente a cobrança. Limitar tamanho das coletas, armazenamento e exportações, e evitar expansão automática de recursos sem teto acordado.

## Analytics

**Sim, haverá painel para acompanhar acessos mensais.** Recomendação inicial: Cloudflare Web Analytics, com acesso restrito ao responsável pelo projeto.

Registrar no relatório mensal visitas, visualizações de páginas, páginas mais acessadas, origens de acesso disponíveis e desempenho. A ferramenta oferece métricas de visitas, page views e experiência de carregamento; conferir as dimensões e a retenção disponíveis no momento da configuração. [Definição oficial das métricas](https://developers.cloudflare.com/web-analytics/data-metrics/high-level-metrics/).

Uma visita não é uma pessoa única: o mesmo indivíduo pode gerar várias visitas. A definição do fornecedor deve acompanhar o relatório. Bloqueadores, JavaScript desabilitado e critérios de medição geram diferenças; não vender o painel como contagem exata de pessoas.

O tráfego técnico da CDN inclui robôs e requisições que não equivalem a visitas humanas. Separar analytics de audiência de métricas de operação (erros, latência, disponibilidade, atraso de coleta e custos).

Não capturar termos livres de busca, documentos pessoais, tokens ou parâmetros sensíveis. Não criar perfis individuais de preferência política nem gravar sessões. Configurar páginas/rotas de forma a evitar vazamento de dados em URLs. Revisar periodicamente scripts de terceiros e acesso ao painel.

Consolidar mensalmente indicadores agregados para histórico próprio. Antes de prometer exportação automática e retenção longa, validar as capacidades do plano. GA4, eventos personalizados ou gravação de sessão ficam fora do escopo inicial e exigem nova decisão.

## Privacidade

Publicar aviso de privacidade com finalidades, ferramentas usadas, responsáveis e canal de contato. Mapear também logs de segurança e contatos recebidos. Analytics descrito pelo fornecedor como voltado à privacidade não dispensa essa avaliação. Definir necessidade de consentimento e outras bases legais a partir da configuração real, considerando o [guia da ANPD sobre cookies](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_cookies_e_protecao_de_dados_pessoais).

Dados públicos não justificam reproduzir todo dado pessoal encontrado. Limitar a coleta à atuação pública e evitar expor CPF, endereços residenciais ou contatos particulares.
