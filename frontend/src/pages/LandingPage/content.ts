/**
 * Conteúdo institucional real, recebido da organização — nunca modalidade
 * inventada. O Instituto mantém hoje dois projetos, não três: SoulBallet
 * (balé e música juntos) e Livre Acesso ao Esporte (Jiu-Jitsu).
 */

export const marqueeWords = [
  'CUIDADO',
  'COMUNIDADE',
  'ARTE',
  'ESPORTE',
  'DESDE 2010',
  'CEILÂNDIA',
  'CIDADANIA',
  'PERTENCIMENTO',
]

export const aboutParagraph =
  'O Instituto Livre Acesso é uma organização não governamental criada em agosto de 2010, ' +
  'em Ceilândia Norte, no Distrito Federal, a partir da iniciativa de pessoas atuantes em ' +
  'prol da solidariedade e do trabalho em conjunto pelo bem social da comunidade. ' +
  'Desenvolvemos projetos de cultura e educação para comunidades carentes, porque só pela ' +
  'responsabilidade social e pela promoção da dignidade humana a sociedade consegue minimizar ' +
  'os danos dos males modernos que afetam nossa juventude.'

export interface Program {
  number: string
  name: string
  since: string
  summary: string
  description: string
  methodology?: string[]
  image: { src: string; alt: string }
}

export const programs: Program[] = [
  {
    number: '01',
    name: 'SoulBallet',
    since: 'Desde 2010',
    summary: 'Balé e música como instrumentos de ética, cidadania e autonomia.',
    description:
      'O SoulBallet nasceu em 2010 com a missão de usar a prática do balé e da música para ' +
      'ensinar valores éticos, morais e de cidadania. Mais do que aperfeiçoamento técnico, o ' +
      'projeto promove acesso efetivo aos direitos culturais, atuando direto na comunidade de ' +
      'Ceilândia com aulas para crianças, adolescentes e jovens. A proposta pedagógica ' +
      'desenvolve a linguagem e a capacidade perceptiva dos alunos pela consciência corporal, ' +
      'pelo ritmo e pela resposta do corpo ao movimento.',
    methodology: [
      'Balé clássico — técnica de Agrippina Vaganova',
      'Dança contemporânea — estudos de movimento de Rudolf Laban',
      'Dança espanhola — Escola Bolera, flamenco e clássico espanhol',
    ],
    image: { src: '/landing/soulballet-recital.webp', alt: 'Turma do SoulBallet reunida no palco após um recital' },
  },
  {
    number: '02',
    name: 'Livre Acesso ao Esporte',
    since: 'Jiu-Jitsu',
    summary: 'Jiu-Jitsu como resposta ativa, com o aluno no centro do próprio aprendizado.',
    description:
      'O Projeto Livre Acesso ao Esporte – Jiu-Jitsu une esforços articulados para transformar ' +
      'a trajetória de crianças e adolescentes da região, abrindo espaço para novas ' +
      'oportunidades. Por meio de uma metodologia ativa, colocamos os participantes como ' +
      'protagonistas do próprio aprendizado, estimulando autonomia e motivação. A programação ' +
      'inclui práticas corporais e conteúdos teóricos, individuais e coletivos, respeitando o ' +
      'conhecimento prévio de cada aluno, com acompanhamento de profissionais especializados.',
    image: { src: '/landing/jiujitsu-equipe.webp', alt: 'Equipe de Jiu-Jitsu do Instituto Livre Acesso reunida' },
  },
]
