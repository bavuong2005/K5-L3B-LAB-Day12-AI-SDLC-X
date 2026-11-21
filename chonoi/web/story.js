/* Truyen "Quan An Cho Noi" - du lieu thuan, viet nguyen goc. Moi dong: {who, text<=120 ky tu}. */
(function () {
  var S = function (t) { return { who: 'sen', text: t }; };
  var B = function (t) { return { who: 'batu', text: t }; };
  var C = function (t) { return { who: 'chuba', text: t }; };
  var H = function (t) { return { who: 'haibap', text: t }; };
  var K = function (t) { return { who: 'casau', text: t }; };

  var story = {
    version: 1,
    cast: {
      sen:    { name: 'Trường con',          role: 'Thợ lặn, chủ quán',            color: '#ffb703' },
      batu:   { name: 'Bà Tư',           role: 'Bà nội, thầy nấu ăn',           color: '#e76f51' },
      chuba:  { name: 'Chú Ba Chèo',     role: 'Lái ghe già, hay kể chuyện',    color: '#2a9d8f' },
      haibap: { name: 'Cô Hai Bắp',      role: 'Chủ quán đối thủ, khách khó tính', color: '#9b5de5' },
      casau:  { name: 'Cá Sấu Năm Chèo', role: 'Thủy quái hay đòi ăn',          color: '#6a994e' }
    },

    intro: [
      B('Trường con, dậy đi! Nắng lên tới ngọn dừa rồi.'),
      S('Dạ, con dậy rồi... con mơ thấy cái nồi đồng của ông cố nữa.'),
      B('Nồi đó chìm xuống sông từ hồi bà còn nhỏ. Mơ hoài chi cho mệt.'),
      S('Con sẽ lặn tìm. Sáng bắt cá, hái bông. Tối mở quán trên ghe.'),
      B('Ừ, 5 ngày. Quán hết khách thì bà cũng hết tiền mua mắm.'),
      C('Nghe nói dưới sâu có con Cá Sấu bự lắm. Tên Năm Chèo.'),
      S('Tên gì mà nghe giống... người chèo ghe vậy chú?'),
      C('Thì nó đớp mất của chú năm cái chèo rồi đó con.'),
      S('Dạ... con lặn đây. Nhớ giữ hơi thở nghen!')
    ],

    days: {
      1: {
        pre: [
          B('Hôm nay làm quen thôi. Lặn nhẹ nhẹ, đừng ham.'),
          S('Đi dọc bờ, hái bông súng. Bắt cá lóc nữa là đủ.'),
          C('Hơi thở của con có hạn. Thấy nhẹ là bơi về bến liền.'),
          S('Dạ! WASD để bơi, Space để bắt cá, E để hái.')
        ],
        post: [
          B('Cá lóc nướng trui với gỏi bông súng, mỗi món ba phần.'),
          S('Con làm xong rồi! Khách ăn mà khen không ngớt.'),
          K('Ục... ục... (Có mùi cá nướng. Năm Chèo đang đói.)'),
          B('Ngày đầu coi như đậu. Mai nhớ canh cá cho kỹ.')
        ]
      },
      2: {
        pre: [
          B('Hôm nay có lẩu cá linh bông điên điển. Cần sáu con cá linh.'),
          S('Sáu con cá linh nhỏ xíu, bắt hoài mới đủ.'),
          B('Cá để lâu là ươn. Tươi dưới 30 là khách chê đó nghen.'),
          S('Dạ, con bắt xong là về bến nấu liền, không la cà.')
        ],
        post: [
          H('Lẩu cá linh của con bé này... được đó. Cá còn tươi roi rói.'),
          S('Dạ cám ơn cô Hai! Cô cứ ghé hoài nghen.'),
          H('Ghé coi chứ không phải khen đâu. Đừng có mừng.'),
          B('Cô Hai khen kiểu đó là khen thiệt rồi con.')
        ]
      },
      3: {
        pre: [
          C('Hôm nay con lặn ra vùng sâu. Có thêm một con Cá Sấu nữa.'),
          S('Dạ?! Con kia tên gì vậy chú?'),
          C('Chưa đặt tên. Con thấy mặt nó cau có, kêu Sáu Cau đi.'),
          B('Thấy nó rượt là bơi lên liền. Cá nào cũng không bằng cái mạng.'),
          S('Hôm nay cần cá kéo bốn con, cá lóc hai con, bông súng bốn.')
        ],
        post: [
          S('Con bị đớp mất mấy con cá... nhưng con còn nguyên!'),
          K('Hự. (Cá Sấu quay đi, hình như hơi ngại.)'),
          C('Lạ à nghen. Nó đòi cá chứ không cắn con. Có chuyện gì đó.'),
          B('Canh chua cá lóc với cá kéo nướng hôm nay ngon hết sảy.')
        ]
      },
      4: {
        pre: [
          B('Hôm nay khách lớn tới. Có đoàn ghe từ Cần Thơ xuống.'),
          S('Con phải nấu lẩu mắm. Món này cần bốn nguyên liệu.'),
          H('Lẩu mắm hả? Để cô coi con làm nổi không.'),
          B('Khách chờ lâu là giận, mà uy tín thì rớt khó lên lại.'),
          S('Dạ, con nấu nhanh, bưng đúng bàn. Con làm được.')
        ],
        post: [
          H('Nước lẩu này... giống y chang của bà Tư hồi xưa.'),
          B('Ủa, cô Hai biết công thức hồi xưa của bà hả?'),
          H('Biết chứ. Cô từng ăn nó, ở dưới con sông này. Lúc đó cô nhỏ xíu.'),
          S('Dưới sông? Vậy cái nồi đồng... có thể ở gần Cá Sấu!')
        ]
      },
      5: {
        pre: [
          B('Ngày cuối. Có cá lóc, lẩu cá linh, rồi lẩu mắm nữa.'),
          C('Chú chèo ghe đưa con ra chỗ sâu nhất. Hơi thở nhớ canh nghen.'),
          S('Con nâng oxy lên rồi, chắc đủ lặn tới đáy.'),
          H('Cô cũng đi theo. Cô muốn thấy cái nồi đó lần nữa.'),
          S('Dạ. Mình đi thôi, cả nhà mình cùng lặn!')
        ],
        post: [
          K('Ục ục ục. (Năm Chèo đẩy cái nồi đồng ra, chờ ăn lẩu.)'),
          S('Nồi đồng nè! Hóa ra chú Năm Chèo giữ giùm hoài!'),
          B('Cái ông này, giữ nồi bà mấy chục năm mà hổng chịu nói.'),
          C('Nó đâu nói được. Nó chỉ đòi cá, đòi lẩu, tội nghiệp.'),
          S('Vậy tối nay quán mình có thêm một vị khách quen!')
        ]
      }
    },

    ending: {
      good: [
        B('Quán đông khách, danh tiếng vang khắp chợ nổi.'),
        H('Cô thua rồi, Trường con. Quán con ngon hơn quán cô.'),
        S('Cô Hai ơi, sáng mai qua phụ con nghen!'),
        C('Cả chợ nổi giờ ai cũng biết quán Trường con.'),
        K('Ục! (Năm Chèo ngoi lên đòi thêm một tô lẩu mắm.)'),
        S('Nồi đồng về nhà rồi. Quán Trường con mở cửa mỗi ngày!')
      ],
      ok: [
        B('Quán qua được 5 ngày, tuy chưa nổi tiếng lắm.'),
        H('Cũng được. Lần sau nhớ canh khách cho kỹ.'),
        S('Dạ, con học được nhiều rồi. Con sẽ cố hơn.'),
        C('Có nồi đồng rồi, còn lại cứ từ từ mà làm.'),
        K('Ục. (Năm Chèo gật đầu, hứa ngày mai đến ăn tiếp.)')
      ],
      bad: [
        B('Quán vắng khách, bà thấy buồn lắm con à.'),
        S('Con xin lỗi bà. Con làm khách giận, cá ươn nhiều quá.'),
        H('Đừng nản. Cô cũng dở hồi mới mở quán.'),
        C('Ngủ một giấc, mai lặn lại. Sông không đi đâu hết.'),
        K('Ục... (Năm Chèo cũng buồn, đẩy tới một con cá an ủi.)')
      ]
    },

    tips: [
      'Bơi về bến khi oxy còn một chút, đừng đợi tới giây cuối.',
      'Cá để lâu sẽ ươn. Nấu sớm thì món bán được giá cao hơn.',
      'Cá Sấu chỉ đuổi ở vùng sâu. Thấy nó rượt thì bơi lên gần mặt nước.',
      'Bị Cá Sấu đớp thì mất nửa giỏ. Giữ khoảng cách cho chắc.',
      'Khách chờ quá lâu sẽ giận bỏ đi. Uy tín tụt là khó lên lại.',
      'Phục vụ nhanh còn được boa, và boa giúp uy tín lên.',
      'Mua nâng cấp oxy và máu ở Shop để lặn sâu hơn, bền hơn.',
      'Nhớ xem kế hoạch món của ngày để biết hôm nay cần nguyên liệu gì.'
    ],

    reasonForQuan: [
      'Hết hơi rồi. Bơi lên bến, tối nay còn mở quán.',
      'Hết giờ lặn. Về bến thôi Trường con.',
      'Cá Sấu đớp ngất rồi. Mai lặn lại, quán vẫn mở nghen.',
      'Giỏ đầy rồi. Về bến nấu cho khách thôi.'
    ]
  };

  function pickEnding(r) {
    r = r || {};
    var score = +r.score || 0;
    var rep = +r.reputation || 0;
    var days = +r.days_completed || 0;
    if (days >= 5 && rep >= 4 && score >= 1200) return 'good';
    if (days >= 5 && (rep >= 2.5 || score >= 700)) return 'ok';
    if (days < 5 && rep >= 3) return 'ok';
    return 'bad';
  }

  story.pickEnding = pickEnding;
  story.getEnding = function (r) { return story.ending[pickEnding(r)]; };

  if (typeof window !== 'undefined') window.ChoNoiStory = story;
  if (typeof module !== 'undefined' && module.exports) module.exports = story;
})();
