SELECT 
    ticker, 
    company_name, 
    open_price, 
    close_price, 
    country, 
    exchange, 
    sector, 
    specialization, 
    ((close_price - open_price) / open_price) * 100 AS percent_change
FROM 
    stocks
WHERE 
    ((close_price - open_price) / open_price) * 100 < -5
ORDER BY 
    percent_change ASC;

    SELECT 
    ticker, 
    company_name, 
    open_price, 
    close_price, 
    country, 
    exchange, 
    sector, 
    specialization, 
    ((close_price - open_price) / open_price) * 100 AS percent_change
FROM 
    stocks
WHERE 
    ((close_price - open_price) / open_price) * 100 > 5
ORDER BY 
    percent_change DESC;


    SELECT 
    ticker, 
    company_name, 
    open_price, 
    close_price, 
    country, 
    exchange, 
    sector, 
    specialization, 
    volume
FROM 
    stocks
ORDER BY 
    volume DESC
LIMIT 10;


CREATE TABLE stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    open_price DECIMAL(10, 2) NOT NULL,
    close_price DECIMAL(10, 2) NOT NULL,
    country VARCHAR(100) NOT NULL,
    exchange VARCHAR(100) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    volume BIGINT NOT NULL,
    timestamp DATETIME NOT NULL
);


INSERT INTO stocks (ticker, company_name, open_price, close_price, country, exchange, sector, specialization, volume, timestamp)
VALUES
-- Failers (Stocks with a decrease of more than 5%)
('AAPL', 'Apple Inc.', 150.00, 140.00, 'USA', 'NASDAQ', 'Technology', 'Consumer Electronics', 10000000, NOW()),
('MSFT', 'Microsoft Corporation', 300.00, 285.00, 'USA', 'NASDAQ', 'Technology', 'Software', 8000000, NOW()),
('GOOGL', 'Alphabet Inc.', 2800.00, 2650.00, 'USA', 'NASDAQ', 'Technology', 'Internet Services', 5000000, NOW()),
('AMZN', 'Amazon.com Inc.', 3400.00, 3200.00, 'USA', 'NASDAQ', 'Consumer Discretionary', 'E-commerce', 7000000, NOW()),
('TSLA', 'Tesla Inc.', 900.00, 850.00, 'USA', 'NASDAQ', 'Automotive', 'Electric Vehicles', 12000000, NOW()),
('NFLX', 'Netflix Inc.', 600.00, 570.00, 'USA', 'NASDAQ', 'Communication Services', 'Streaming', 3000000, NOW()),
('NVDA', 'NVIDIA Corporation', 800.00, 760.00, 'USA', 'NASDAQ', 'Technology', 'Semiconductors', 9000000, NOW()),
('INTC', 'Intel Corporation', 50.00, 47.00, 'USA', 'NASDAQ', 'Technology', 'Semiconductors', 6000000, NOW()),
('PYPL', 'PayPal Holdings Inc.', 250.00, 235.00, 'USA', 'NASDAQ', 'Financials', 'Digital Payments', 4000000, NOW()),
('DIS', 'The Walt Disney Company', 180.00, 170.00, 'USA', 'NYSE', 'Communication Services', 'Entertainment', 5000000, NOW()),

-- Gainers (Stocks with an increase of more than 5%)
('META', 'Meta Platforms Inc.', 350.00, 370.00, 'USA', 'NASDAQ', 'Technology', 'Social Media', 10000000, NOW()),
('GOOG', 'Alphabet Inc.', 2800.00, 2940.00, 'USA', 'NASDAQ', 'Technology', 'Internet Services', 5000000, NOW()),
('BABA', 'Alibaba Group Holding Limited', 150.00, 160.00, 'China', 'NYSE', 'Consumer Discretionary', 'E-commerce', 8000000, NOW()),
('AMD', 'Advanced Micro Devices Inc.', 120.00, 130.00, 'USA', 'NASDAQ', 'Technology', 'Semiconductors', 7000000, NOW()),
('SPY', 'SPDR S&P 500 ETF Trust', 450.00, 470.00, 'USA', 'NYSE', 'ETF', 'Index Fund', 20000000, NOW()),
('BRK-B', 'Berkshire Hathaway Inc.', 350.00, 370.00, 'USA', 'NYSE', 'Financials', 'Conglomerate', 3000000, NOW()),
('V', 'Visa Inc.', 250.00, 265.00, 'USA', 'NYSE', 'Financials', 'Digital Payments', 4000000, NOW()),
('WMT', 'Walmart Inc.', 150.00, 160.00, 'USA', 'NYSE', 'Consumer Staples', 'Retail', 6000000, NOW()),
('JNJ', 'Johnson & Johnson', 170.00, 180.00, 'USA', 'NYSE', 'Healthcare', 'Pharmaceuticals', 5000000, NOW()),
('GE', 'General Electric Company', 100.00, 105.00, 'USA', 'NYSE', 'Industrials', 'Conglomerate', 4000000, NOW()),

-- Most Activities (Stocks with high trading volume)
('INTU', 'Intuit Inc.', 500.00, 510.00, 'USA', 'NASDAQ', 'Technology', 'Software', 15000000, NOW()),
('ADBE', 'Adobe Inc.', 600.00, 610.00, 'USA', 'NASDAQ', 'Technology', 'Software', 14000000, NOW()),
('BA', 'The Boeing Company', 200.00, 210.00, 'USA', 'NYSE', 'Industrials', 'Aerospace', 13000000, NOW()),
('XOM', 'Exxon Mobil Corporation', 80.00, 85.00, 'USA', 'NYSE', 'Energy', 'Oil & Gas', 12000000, NOW()),
('T', 'AT&T Inc.', 25.00, 26.00, 'USA', 'NYSE', 'Communication Services', 'Telecom', 11000000, NOW()),
('ORCL', 'Oracle Corporation', 90.00, 95.00, 'USA', 'NYSE', 'Technology', 'Software', 10000000, NOW()),
('CSCO', 'Cisco Systems Inc.', 55.00, 58.00, 'USA', 'NASDAQ', 'Technology', 'Networking', 9000000, NOW()),
('PFE', 'Pfizer Inc.', 50.00, 52.00, 'USA', 'NYSE', 'Healthcare', 'Pharmaceuticals', 8000000, NOW()),
('UPS', 'United Parcel Service Inc.', 200.00, 210.00, 'USA', 'NYSE', 'Industrials', 'Logistics', 7000000, NOW()),
('MCD', 'McDonald\'s Corporation', 250.00, 260.00, 'USA', 'NYSE', 'Consumer Discretionary', 'Restaurants', 6000000, NOW()),

-- Sector Trends (Stocks in specific sectors)
('CVX', 'Chevron Corporation', 120.00, 125.00, 'USA', 'NYSE', 'Energy', 'Oil & Gas', 5000000, NOW()),
('BIDU', 'Baidu Inc.', 150.00, 155.00, 'China', 'NASDAQ', 'Technology', 'Internet Services', 4000000, NOW()),
('GS', 'The Goldman Sachs Group Inc.', 400.00, 410.00, 'USA', 'NYSE', 'Financials', 'Investment Banking', 3000000, NOW()),
('MCD', 'McDonald\'s Corporation', 250.00, 260.00, 'USA', 'NYSE', 'Consumer Discretionary', 'Restaurants', 6000000, NOW()),
('JNJ', 'Johnson & Johnson', 170.00, 180.00, 'USA', 'NYSE', 'Healthcare', 'Pharmaceuticals', 5000000, NOW()),
('GE', 'General Electric Company', 100.00, 105.00, 'USA', 'NYSE', 'Industrials', 'Conglomerate', 4000000, NOW()),
('INTU', 'Intuit Inc.', 500.00, 510.00, 'USA', 'NASDAQ', 'Technology', 'Software', 15000000, NOW()),
('ADBE', 'Adobe Inc.', 600.00, 610.00, 'USA', 'NASDAQ', 'Technology', 'Software', 14000000, NOW()),
('BA', 'The Boeing Company', 200.00, 210.00, 'USA', 'NYSE', 'Industrials', 'Aerospace', 13000000, NOW()),
('XOM', 'Exxon Mobil Corporation', 80.00, 85.00, 'USA', 'NYSE', 'Energy', 'Oil & Gas', 12000000, NOW()),

-- Volatility (Stocks with high volatility)
('TSLA', 'Tesla Inc.', 900.00, 950.00, 'USA', 'NASDAQ', 'Automotive', 'Electric Vehicles', 12000000, NOW()),
('NVDA', 'NVIDIA Corporation', 800.00, 850.00, 'USA', 'NASDAQ', 'Technology', 'Semiconductors', 9000000, NOW()),
('AMD', 'Advanced Micro Devices Inc.', 120.00, 130.00, 'USA', 'NASDAQ', 'Technology', 'Semiconductors', 7000000, NOW()),
('PYPL', 'PayPal Holdings Inc.', 250.00, 260.00, 'USA', 'NASDAQ', 'Financials', 'Digital Payments', 4000000, NOW()),
('DIS', 'The Walt Disney Company', 180.00, 190.00, 'USA', 'NYSE', 'Communication Services', 'Entertainment', 5000000, NOW()),
('META', 'Meta Platforms Inc.', 350.00, 370.00, 'USA', 'NASDAQ', 'Technology', 'Social Media', 10000000, NOW()),
('GOOG', 'Alphabet Inc.', 2800.00, 2940.00, 'USA', 'NASDAQ', 'Technology', 'Internet Services', 5000000, NOW()),
('BABA', 'Alibaba Group Holding Limited', 150.00, 160.00, 'China', 'NYSE', 'Consumer Discretionary', 'E-commerce', 8000000, NOW()),
('SPY', 'SPDR S&P 500 ETF Trust', 450.00, 470.00, 'USA', 'NYSE', 'ETF', 'Index Fund', 20000000, NOW()),
('BRK-B', 'Berkshire Hathaway Inc.', 350.00, 370.00, 'USA', 'NYSE', 'Financials', 'Conglomerate', 3000000, NOW());