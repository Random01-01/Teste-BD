-- ==========================================================
-- SISTEMA DE AGENDAMENTO - BANCO DE DADOS COMPLETO
-- UNIVESP - Projeto Integrador
-- Compatível com MySQL Workbench 8.0+
-- ==========================================================

DROP DATABASE IF EXISTS sistema_agendamento;
CREATE DATABASE sistema_agendamento CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sistema_agendamento;

-- 1. PROFISSIONAL
CREATE TABLE profissional (
    id_profissional INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20),
    email VARCHAR(100) UNIQUE NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. CATEGORIA DE SERVIÇO
CREATE TABLE categoria_servico (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- 3. CLIENTE
CREATE TABLE cliente (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. USUARIO ADMINISTRATIVO
CREATE TABLE usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    id_profissional INT NOT NULL,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    perfil VARCHAR(30) DEFAULT 'ADMIN',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_profissional FOREIGN KEY (id_profissional) REFERENCES profissional(id_profissional) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 5. SERVIÇO
CREATE TABLE servico (
    id_servico INT AUTO_INCREMENT PRIMARY KEY,
    id_profissional INT NOT NULL,
    id_categoria INT,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL,
    duracao_minutos INT NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_servico_profissional FOREIGN KEY (id_profissional) REFERENCES profissional(id_profissional) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_servico_categoria FOREIGN KEY (id_categoria) REFERENCES categoria_servico(id_categoria) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 6. HORÁRIO DISPONÍVEL
CREATE TABLE horario_disponivel (
    id_horario INT AUTO_INCREMENT PRIMARY KEY,
    id_profissional INT NOT NULL,
    dia_semana ENUM('Segunda','Terca','Quarta','Quinta','Sexta','Sabado','Domingo') NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    CONSTRAINT fk_horario_profissional FOREIGN KEY (id_profissional) REFERENCES profissional(id_profissional) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 7. AGENDAMENTO
CREATE TABLE agendamento (
    id_agendamento INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_servico INT NOT NULL,
    id_profissional INT NOT NULL,
    data_agendamento DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    status ENUM('CONFIRMADO','CANCELADO','CONCLUIDO','PENDENTE') DEFAULT 'CONFIRMADO',
    observacao TEXT,
    motivo_cancelamento VARCHAR(255) NULL,
    data_cancelamento DATETIME NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agendamento_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente) ON UPDATE CASCADE,
    CONSTRAINT fk_agendamento_servico FOREIGN KEY (id_servico) REFERENCES servico(id_servico) ON UPDATE CASCADE,
    CONSTRAINT fk_agendamento_profissional FOREIGN KEY (id_profissional) REFERENCES profissional(id_profissional) ON UPDATE CASCADE,
    INDEX idx_agendamento_data_prof (data_agendamento, id_profissional, hora_inicio)
) ENGINE=InnoDB;

-- 8. TRIGGER: REGRA PARA IMPEDIR CONFLITO DE HORÁRIOS
DELIMITER $$
CREATE TRIGGER trg_impede_conflito_horario
BEFORE INSERT ON agendamento
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM agendamento
        WHERE id_profissional = NEW.id_profissional
        AND data_agendamento = NEW.data_agendamento
        AND status != 'CANCELADO'
        AND (NEW.hora_inicio < hora_fim AND NEW.hora_fim > hora_inicio)
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'ERRO: Conflito de horário! Esta profissional já possui agendamento neste intervalo.';
    END IF;
END$$

CREATE TRIGGER trg_impede_conflito_horario_update
BEFORE UPDATE ON agendamento
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM agendamento
        WHERE id_profissional = NEW.id_profissional
        AND data_agendamento = NEW.data_agendamento
        AND id_agendamento != NEW.id_agendamento
        AND status != 'CANCELADO'
        AND (NEW.hora_inicio < hora_fim AND NEW.hora_fim > hora_inicio)
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'ERRO: Conflito de horário ao tentar alterar!';
    END IF;
END$$
DELIMITER ;

-- 9. DADOS PARA TESTE
INSERT INTO profissional (nome, telefone, email) VALUES ('Mariana Souza', '(18) 99999-1111', 'mariana@email.com');
INSERT INTO categoria_servico (nome) VALUES ('Cabelo'), ('Estética'), ('Manicure e Pedicure');
INSERT INTO usuario (id_profissional, nome, email, senha_hash) VALUES (1, 'Mariana Admin', 'admin@mariana.com', '$2b$12$hash_exemplo_123');
INSERT INTO cliente (nome, telefone, email) VALUES 
('Ana Paula', '(18) 98888-2222', 'ana@email.com'),
('Juliana Santos', '(18) 97777-3333', 'juliana@email.com'),
('Carla Mendes', '(18) 96666-4444', 'carla@email.com');

INSERT INTO servico (id_profissional, id_categoria, nome, descricao, preco, duracao_minutos) VALUES 
(1, 1, 'Corte feminino', 'Corte de cabelo feminino', 60.00, 60),
(1, 1, 'Escova', 'Escova modelada', 45.00, 45),
(1, 1, 'Coloração', 'Coloração completa', 150.00, 120),
(1, 2, 'Design de sobrancelha', 'Design com henna', 50.00, 30);

INSERT INTO horario_disponivel (id_profissional, dia_semana, hora_inicio, hora_fim) VALUES
(1, 'Segunda', '09:00', '18:00'),
(1, 'Terca', '09:00', '18:00'),
(1, 'Quarta', '09:00', '18:00'),
(1, 'Quinta', '09:00', '18:00'),
(1, 'Sexta', '09:00', '18:00'),
(1, 'Sabado', '09:00', '13:00');

INSERT INTO agendamento (id_cliente, id_servico, id_profissional, data_agendamento, hora_inicio, hora_fim, status) VALUES
(1, 1, 1, '2026-10-06', '10:00', '11:00', 'CONFIRMADO'),
(2, 2, 1, '2026-10-06', '11:30', '12:15', 'CONFIRMADO');
