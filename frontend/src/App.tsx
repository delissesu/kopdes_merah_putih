import { useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate, useLocation, Navigate } from 'react-router-dom';
import './App.css';
import type { Product, CartItem } from './types';
import { ProductList } from './pages/ProductList';
import { ProductDetail } from './pages/ProductDetail';
import { Cart } from './pages/Cart';
import { Checkout } from './pages/Checkout';
import { Login } from './pages/Login';

const API_BASE = 'http://localhost:8000';

interface CartSummary {
  subtotal: number;
  voucher_discount: number;
  member_discount: number;
  cashback: number;
  total_to_pay: number;
}

interface PaymentDetail {
  subtotal: number;
  voucher_discount: number;
  member_discount: number;
  cashback: number;
  total_paid: number;
  new_balance: number;
}

function App() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [showPopup, setShowPopup] = useState<boolean>(false);
  const [voucher, setVoucher] = useState<string>('');
  const [appliedVouchers, setAppliedVouchers] = useState<string[]>([]);
  const [cartSummary, setCartSummary] = useState<CartSummary | null>(null);
  const [paymentResult, setPaymentResult] = useState<PaymentDetail | null>(null);

  // Initialize state from localStorage
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => {
    return localStorage.getItem('user') !== null;
  });
  const [user, setUser] = useState<any>(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [balance, setBalance] = useState<number>(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser).balance : 0;
  });
  const [isMember] = useState<boolean>(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser).is_member : false;
  });

  const navigate = useNavigate();
  const location = useLocation();

  const fetchCart = async (userId: number) => {
    try {
      const res = await fetch(`${API_BASE}/cart/${userId}`);
      if (res.ok) {
        const data = await res.json();
        const mappedCart = data.map((item: any) => ({
          product: {
            id: item.id,
            name: item.name,
            description: item.description,
            price: item.price,
            image: `https://placehold.co/400x300/ff5e5b/000?text=${item.name.toUpperCase().replace(/ /g, '+')}`
          },
          qty: item.quantity
        }));
        setCart(mappedCart);
      }
    } catch (error) {
      console.error('Failed to fetch cart:', error);
    }
  };

  const fetchCartSummary = async (userId: number, voucherNames: string[]) => {
    if (cart.length === 0 && appliedVouchers.length === 0 && voucherNames.length === 0) {
      setCartSummary(null);
      return;
    }
    try {
      const params = new URLSearchParams();
      voucherNames.forEach(v => params.append('voucherNames', v));
      const res = await fetch(`${API_BASE}/cart/summary/${userId}?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setCartSummary(data);
      }
    } catch (error) {
      console.error('Failed to fetch cart summary:', error);
    }
  };

  useEffect(() => {
    if (isLoggedIn && user) {
      fetchCart(user.id);
    }
  }, [isLoggedIn, user]);

  // Refresh summary ketika cart atau voucher berubah
  useEffect(() => {
    if (isLoggedIn && user && cart.length > 0) {
      fetchCartSummary(user.id, appliedVouchers);
    } else {
      setCartSummary(null);
    }
  }, [cart, appliedVouchers]);

  const handleAddToCart = async (product: Product, qty: number) => {
    if (!user) {
      alert('Silakan login terlebih dahulu');
      navigate('/login');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/cart/add/product`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: user.id,
          productId: product.id,
          quantity: qty
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.Status === 'Success') {
          await fetchCart(user.id);
          setShowPopup(true);
          setTimeout(() => setShowPopup(false), 2000);
        } else {
          alert(data.Message || 'Gagal menambahkan ke keranjang');
        }
      }
    } catch (error) {
      console.error('Failed to add to cart:', error);
      alert('Terjadi kesalahan saat menambahkan ke keranjang');
    }
  };

  const handleApplyVoucher = async () => {
    const code = voucher.toUpperCase().trim();
    if (!code) return;

    if (appliedVouchers.includes(code)) {
      alert('Voucher ini sudah diterapkan!');
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE}/vouchers/check?userId=${user.id}&voucherName=${encodeURIComponent(code)}`
      );
      const data = await res.json();

      if (data.Valid) {
        setAppliedVouchers(prev => [...prev, code]);
        setVoucher('');
        alert(`Voucher "${code}" berhasil diterapkan!`);
      } else {
        alert(data.Message || 'Voucher tidak valid!');
      }
    } catch (error) {
      console.error('Failed to check voucher:', error);
      alert('Terjadi kesalahan saat memeriksa voucher');
    }
  };

  const calculateSubtotal = () => {
    return cart.reduce((total, item) => total + (item.product.price * item.qty), 0);
  };

  const calculateTotal = () => {
    if (cartSummary) return cartSummary.total_to_pay;
    return calculateSubtotal();
  };

  const handleCheckout = async () => {
    if (cart.length === 0) {
      alert('Keranjang belanja kosong!');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/cart/pay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: user.id,
          voucherNames: appliedVouchers
        }),
      });

      const data = await res.json();

      if (data.Status === 'Success') {
        setPaymentResult(data.Detail);
        setBalance(data.Detail.new_balance);
        // Update user di localStorage
        const updatedUser = { ...user, balance: data.Detail.new_balance };
        localStorage.setItem('user', JSON.stringify(updatedUser));
        navigate('/checkout');
      } else {
        alert(data.Message || 'Pembayaran gagal');
      }
    } catch (error) {
      console.error('Failed to process payment:', error);
      alert('Terjadi kesalahan saat memproses pembayaran');
    }
  };

  const resetFlow = () => {
    setCart([]);
    setVoucher('');
    setAppliedVouchers([]);
    setCartSummary(null);
    setPaymentResult(null);
    navigate('/');
  };

  const cartItemCount = cart.reduce((count, item) => count + item.qty, 0);
  const isProductActive = location.pathname === '/' || location.pathname.startsWith('/product');
  const isCartActive = location.pathname === '/cart';

  return (
    <div className="container">
      <header className="header">
        <div className="header-top">
          <div className="header-top-left">
            <h1>Kopdes Merah Putih</h1>
            {isLoggedIn && <span className="user-greeting">Halo, {user?.name}</span>}
          </div>
          {
            isLoggedIn &&
          <div className="balance-badge">Saldo: Rp {balance.toLocaleString('id-ID')}</div>
          }
        </div>
        <div className="step-indicator">
          {isLoggedIn && (
            <>
              <Link to="/" className={`nav-item ${isProductActive ? 'active' : ''}`}>Produk</Link>
              <Link to="/cart" className={`nav-item ${isCartActive ? 'active' : ''}`}>
                Keranjang {cartItemCount > 0 && `(${cartItemCount})`}
              </Link>
            </>
          )}
          {isLoggedIn &&
            <div className="user-menu">
              <button className="nav-item" onClick={() => {
                setIsLoggedIn(false);
                setUser(null);
                localStorage.removeItem('user');
                navigate('/login');
              }}>Logout</button>
            </div>
          }
        </div>
      </header>

      {showPopup && (
        <div className="popup-notification">
          Berhasil ditambahkan ke keranjang!
        </div>
      )}

      <Routes>
        <Route path="/" element={isLoggedIn ? <ProductList /> : <Navigate to="/login" />} />
        <Route path="/product/:id" element={isLoggedIn ? <ProductDetail onAddToCart={handleAddToCart} /> : <Navigate to="/login" />} />
        <Route path="/cart" element={
          isLoggedIn ? (
            <Cart
              cart={cart}
              isMember={isMember}
              voucher={voucher}
              setVoucher={setVoucher}
              appliedVouchers={appliedVouchers}
              handleApplyVoucher={handleApplyVoucher}
              calculateSubtotal={calculateSubtotal}
              calculateTotal={calculateTotal}
              cartSummary={cartSummary}
              handleCheckout={handleCheckout}
            />
          ) : <Navigate to="/login" />
        } />
        <Route path="/checkout" element={
          isLoggedIn ? (
            <Checkout
              paymentResult={paymentResult}
              resetFlow={resetFlow}
            />
          ) : <Navigate to="/login" />
        } />
        <Route path="/login" element={<Login onLogin={(userData) => {
          setIsLoggedIn(true);
          setUser(userData);
          setBalance(userData.balance);
          localStorage.setItem('user', JSON.stringify(userData));
        }} />} />
      </Routes>
    </div>
  );
}

export default App;
